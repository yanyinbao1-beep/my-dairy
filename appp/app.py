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

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "待命", "happiness": 0.5, "stress": 0.2, "weather": "未知", "temp": 25}

st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 实时天气获取函数 ---
def fetch_weather():
    """获取实时天气数据 (北京示例坐标)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=3).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        # 简易代码转换
        mapping = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "小雨", 95: "雷阵雨"}
        desc = mapping.get(code, "多云")
        return desc, temp
    except:
        return "室内", 24.0

current_weather, current_temp = fetch_weather()

# --- 3. 动态 UI 与通知引擎 ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 110)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 25%, 95%); transition: 3s; }}
    .video-container {{ width: 100%; aspect-ratio: 4 / 3; border: 4px solid #5C6BC0; border-radius: 20px; overflow: hidden; background: #000; }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .status-card {{ background: white; border-radius: 15px; padding: 20px; border-top: 10px solid hsl({h_val}, 70%, 50%); box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
    </style>
    <script>
    window.parent.activateNotify = function() {{
        Notification.requestPermission().then(p => {{
            if(p === "granted") new Notification("✅ 天气与情感监测已同步");
            else alert("请在地址栏锁头处允许通知");
        }});
    }};
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') new Notification(t, {{body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'}});
    }};
    </script>
""", unsafe_allow_html=True)

# --- 4. 逻辑处理 ---

if st.session_state.current_page == "main":
    st.title("🤖 机器人多模态监测站")
    
    # 顶部状态栏
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: st.button("🔔 激活 Mac 通知权限", on_click=lambda: components.html("<script>window.parent.activateNotify();</script>", height=0))
    with c2: st.metric("当前气温", f"{current_temp} ℃")
    with c3: st.metric("当前天气", current_weather)

    # 60秒分析周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在结合天气分析你的状态..."):
            try:
                prompt = f"""
                环境:天气{current_weather},气温{current_temp}度。面部特征:{st.session_state.face_log[-6:]}。
                作为AI，请结合天气(如雨天是否让你抑郁)分析用户：
                1. 识别核心情绪标签（开心、悲伤、焦虑、疲惫等）。
                2. 生成一段暖心关怀话。
                JSON: {{"label":"情绪标签","text":"对话","happiness":0.5,"stress":0.2}}
                """
                resp = client.chat.completions.create(
                    model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                record = {
                    "time": datetime.now().strftime("%H:%M"),
                    "label": data['label'], "message": data['text'],
                    "happiness": data['happiness'], "stress": data['stress'],
                    "weather": current_weather, "temp": current_temp
                }
                st.session_state.chat_log.insert(0, record)
                st.session_state.last_metrics = record
                
                # 发送通知
                js_push = f"<script>window.parent.sendPush('监测提醒：{record['label']}', '{record['message']}');</script>"
                components.html(js_push, height=0)
            except: pass

    # UI 渲染
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("📷 观察窗口")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=300)
        f_current = random.choice(["视线聚焦", "面部放松", "神情平稳"])
        st.session_state.face_log.append(f_current)
        st.info(f"🧬 生物特征：{f_current}")

    with r:
        st.subheader("📊 实时情感与环境分析")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div class="status-card">
                <div style="font-size: 0.9em; color: #666;">当前判定 ({cur['weather']})</div>
                <div style="font-size: 2em; font-weight: bold; color: #333;">{cur['label']}</div>
                <div style="color: #444; font-style: italic; border-top: 1px solid #eee; margin-top: 10px; padding-top: 10px;">
                    "{cur['message']}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("📈 进入大数据分析", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据相关性档案")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 趋势图
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        # 2. 天气关联分析
        st.subheader("🌦️ 天气与情感关联度")
        
        weather_analysis = df.groupby("weather")["happiness"].mean()
        st.bar_chart(weather_analysis)
        
        st.divider()
        st.dataframe(df[["time", "label", "weather", "temp", "message"]], use_container_width=True)
    else:
        st.warning("暂无历史数据。")
    
    if st.button("⬅️ 返回主页", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
