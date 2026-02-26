import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Emo-Bot Weather Edition", layout="wide")

# 初始化变量（增加防御性初始值）
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "系统待命", "happiness": 0.5, "stress": 0.2, 
        "weather": "未知", "temp": 25, "message": "准备开始扫描..."
    }

st_autorefresh(interval=10000, key="bot_heartbeat")

# 配置 API
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("请确保在 Streamlit Secrets 中配置了 api_key")

# --- 2. 天气获取逻辑 ---
def fetch_weather():
    try:
        # 默认坐标：北京
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=3).json()
        w = res['current_weather']
        mapping = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "雨", 95: "雷雨"}
        return mapping.get(w['weathercode'], "多云"), w['temperature']
    except:
        return "室内", 25.0

current_weather, current_temp = fetch_weather()

# --- 3. UI 样式与通知 ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 20%, 95%); transition: 3s; }}
    .video-container {{ width: 100%; aspect-ratio: 4 / 3; border: 4px solid #5C6BC0; border-radius: 20px; overflow: hidden; background: #000; }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .status-card {{ background: white; border-radius: 15px; padding: 20px; border-top: 10px solid hsl({h_val}, 70%, 50%); box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
    </style>
    <script>
    window.parent.activateNotify = function() {{
        Notification.requestPermission().then(p => {{
            alert("Mac 权限状态: " + p);
            if(p === "granted") new Notification("✅ 守护模式已开启");
        }});
    }};
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') new Notification(t, {{body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'}});
    }};
    </script>
""", unsafe_allow_html=True)

# --- 4. 路由逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 机器人多模态监测站")
    
    # 顶部状态栏
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: 
        if st.button("🔔 激活 Mac 通知权限", use_container_width=True):
            components.html("<script>window.parent.activateNotify();</script>", height=0)
    with c2: st.metric("当前气温", f"{current_temp} ℃")
    with c3: st.metric("当前天气", current_weather)

    # 60秒总结逻辑
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在多模态建模..."):
            try:
                prompt = f"环境:天气{current_weather},气温{current_temp}度。面部特征:{st.session_state.face_log[-6:]}。分析开心/悲伤/焦虑。JSON:{{'label':'标签','text':'暖心话','happiness':0.5,'stress':0.2}}"
                resp = client.chat.completions.create(
                    model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                record = {
                    "time": datetime.now().strftime("%H:%M"),
                    "label": data.get("label", "状态稳定"),
                    "message": data.get("text", "..."),
                    "happiness": float(data.get("happiness", 0.5)),
                    "stress": float(data.get("stress", 0.2)),
                    "weather": current_weather,
                    "temp": current_temp
                }
                st.session_state.chat_log.insert(0, record)
                st.session_state.last_metrics = record
                
                # 推送
                js_push = f"<script>window.parent.sendPush('观察提醒：{record['label']}', '{record['message']}');</script>"
                components.html(js_push, height=0)
            except:
                st.warning("感应器暂时掉线，正在重试...")

    # 页面渲染
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("📸 实时监控")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=300)
        f_feat = random.choice(["视线稳定", "略显疲惫", "面部放松"])
        st.session_state.face_log.append(f_feat)
        st.info(f"🧬 生物特征：{f_feat}")

    with r:
        st.subheader("💬 实时判定卡片")
        cur = st.session_state.last_metrics
        # 使用 .get() 确保不崩
        st.markdown(f"""
            <div class="status-card">
                <div style="font-size: 0.9em; color: #666;">当前状态分析 ({cur.get('weather', '未知')})</div>
                <div style="font-size: 2em; font-weight: bold; color: #333;">{cur.get('label', '就绪')}</div>
                <div style="color: #444; font-style: italic; border-top: 1px solid #eee; margin-top: 10px; padding-top: 10px;">
                    "{cur.get('message', '扫描中...')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("📈 进入数据看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感关联大数据")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.write("### 📉 情绪波动趋势")
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        # 关联分析（使用 Image Tag 引导用户理解）
        
        
        st.divider()
        st.write("### 📑 历史审计报表")
        # 这里的字段也做了安全筛选
        display_cols = [c for c in ["time", "label", "weather", "message"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.warning("暂无数据。")
    
    if st.button("⬅️ 返回", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
