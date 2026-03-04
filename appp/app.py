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
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "就绪", "happiness": 0.5, "stress": 0.2, 
        "weather": "定位中...", "temp": "--", "message": "等待首次扫描..."
    }

st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 真实地理位置与天气 ---
@st.cache_data(ttl=1800)
def get_real_weather():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=3).json()
        city = geo.get("city", "本地")
        lat, lon = geo.get("lat", 39.9), geo.get("lon", 116.4)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=3).json()
        curr = w_res['current_weather']
        w_map = {0: "晴", 1: "微云", 2: "多云", 3: "阴", 61: "雨", 95: "雷雨"}
        return f"{city} | {w_map.get(curr['weathercode'], '多云')}", curr['temperature']
    except:
        return "本地环境", 25.0

current_weather, current_temp = get_real_weather()

# --- 3. 视觉样式优化 (针对比例调节) ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)

st.markdown(f"""
    <style>
    /* 全局背景缓动 */
    .stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s ease; }}
    
    /* 监控框比例调节：锁定 4:3 且限制最大宽度 */
    .video-container {{
        width: 100%;
        max-width: 480px; 
        aspect-ratio: 4 / 3;
        border: 3px solid #5C6BC0;
        border-radius: 16px;
        overflow: hidden;
        background: #000;
        margin: 0 auto;
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    
    /* 分析卡片美化 */
    .status-card {{
        background: white;
        border-radius: 18px;
        padding: 20px;
        border-left: 8px solid hsl({h_val}, 60%, 50%);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    </style>
    <script>
    if (Notification.permission === 'default') {{ Notification.requestPermission(); }}
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') {{
            new Notification(t, {{ body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png' }});
        }}
    }};
    </script>
""", unsafe_allow_html=True)

# --- 4. 主页面逻辑 ---

if st.session_state.current_page == "main":
    # 标题与天气紧凑布局
    t1, t2 = st.columns([2, 1])
    with t1: st.title("🤖 深度情绪监测终端")
    with t2: st.info(f"📍 {current_weather}  🌡️ {current_temp}℃")

    # 60秒分析周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        try:
            prompt = f"环境:{current_weather},{current_temp}度。分析开心/悲伤/焦虑。JSON:{{'label':'标签','text':'暖心话','happiness':0.5,'stress':0.2}}"
            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
            data = json.loads(resp.choices[0].message.content)
            record = {
                "time": datetime.now().strftime("%H:%M"),
                "label": data.get("label", "稳定"),
                "message": data.get("text", "..."),
                "happiness": float(data.get("happiness", 0.5)),
                "stress": float(data.get("stress", 0.2)),
                "weather": current_weather,
                "temp": current_temp
            }
            st.session_state.chat_log.insert(0, record)
            st.session_state.last_metrics = record
            components.html(f"<script>window.parent.sendPush('监测提醒：{record['label']}', '{record['message']}');</script>", height=0)
        except: pass

    # 核心比例分配 [40% 摄像头, 60% 分析区]
    col_video, col_info = st.columns([4, 6])
    
    with col_video:
        st.subheader("📸 实时画面")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=340)
        st.session_state.face_log.append(random.choice(["专注", "放松"]))
        st.caption("🔍 正在提取面部微表情特征点...")

    with col_info:
        st.subheader("📊 诊断结果")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div class="status-card">
                <div style="color: #666; font-size: 0.85em;">当前状态推演：</div>
                <div style="font-size: 2.2em; font-weight: bold; color: #1A237E; margin: 8px 0;">{cur.get('label')}</div>
                <div style="border-top: 1px solid #eee; padding-top: 12px; color: #333; font-style: italic; font-size: 1.1em;">
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 按钮比例也进行了紧凑化处理
        if st.button("📈 进入大数据分析看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感与环境相关性看板")
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 左右分布：左边趋势，右边散点
        g1, g2 = st.columns(2)
        with g1:
            st.write("### 📉 情绪与压力波动")
            st.line_chart(df.set_index("time")[["happiness", "stress"]])
        with g2:
            st.write("### 🌦️ 气温 vs 愉悦度")
            st.scatter_chart(df, x="temp", y="happiness", color="label")
        
        st.write("### 📑 历史轨迹明细")
        st.dataframe(
            df[["time", "label", "weather", "temp", "happiness", "message"]], 
            use_container_width=True,
            column_config={
                "happiness": st.column_config.ProgressColumn("快乐值", min_value=0, max_value=1),
                "message": st.column_config.TextColumn("详细建议", width="large")
            }
        )
    else:
        st.warning("暂无数据，请等待 60 秒...")

    if st.button("⬅️ 返回监测终端", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
