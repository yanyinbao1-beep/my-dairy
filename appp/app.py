import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 初始化状态
if "welcome_finished" not in st.session_state:
    st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "同步中", "happiness": 0.5, "stress": 0.2, 
        "weather": "定位中...", "temp": "--", "message": "初始化神经网络..."
    }

# --- 2. 封面动图界面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a0c10; }
        .welcome-box {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; height: 85vh;
        }
        .loader {
            width: 120px; height: 120px;
            border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0;
            border-radius: 50%;
            animation: spin 1s linear infinite, glow 2s ease-in-out infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 15px #5C6BC0; } 50% { box-shadow: 0 0 40px #5C6BC0; } }
        .text {
            margin-top: 40px; color: #5C6BC0; font-family: 'SF Pro Display', sans-serif;
            letter-spacing: 8px; font-size: 18px; font-weight: 300;
        }
        </style>
        <div class="welcome-box">
            <div class="loader"></div>
            <div class="text">EMO-BOT INITIALIZING</div>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(2.5) 
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能逻辑 ---
else:
    st_autorefresh(interval=10000, key="bot_heartbeat")
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

    # [自动定位与天气]
    @st.cache_data(ttl=1800)
    def get_context_data():
        try:
            geo = requests.get("http://ip-api.com/json/", timeout=3).json()
            city = geo.get("city", "未知地区")
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true"
            w_res = requests.get(w_url, timeout=3).json()
            temp = w_res['current_weather']['temperature']
            code = w_res['current_weather']['weathercode']
            w_map = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "雨", 95: "雷阵雨"}
            return f"{city} | {w_map.get(code, '多云')}", temp
        except: return "本地环境", 25.0

    current_weather, current_temp = get_context_data()

    # [UI 样式与比例控制]
    m = st.session_state.last_metrics
    h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
    st.markdown(f"""
        <style>
        .stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s ease; }}
        .video-container {{
            width: 100%; max-width: 460px; aspect-ratio: 4 / 3;
            border: 3px solid #5C6BC0; border-radius: 20px;
            overflow: hidden; background: #000; margin: 0 auto;
        }}
        video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
        .status-card {{
            background: white; border-radius: 20px; padding: 25px;
            border-left: 10px solid hsl({h_val}, 60%, 50%);
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 页面路由 ---
    if st.session_state.current_page == "main":
        t1, t2 = st.columns([3, 1])
        with t1: st.title("🤖 深度监测主控台")
        with t2: st.info(f"📍 {current_weather}  🌡️ {current_temp}℃")

        # 分析逻辑
        elapsed = (datetime.now() - st.session_state.start_time).seconds
        if elapsed >= 60:
            st.session_state.start_time = datetime.now()
            try:
                prompt = f"环境:{current_weather}. JSON:{{'label':'标签','text':'暖心话','happiness':0.5,'stress':0.2}}"
                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
                data = json.loads(resp.choices[0].message.content)
                record = {"time": datetime.now().strftime("%H:%M"), "label": data.get("label"), "message": data.get("text"), "happiness": float(data.get("happiness", 0.5)), "stress": float(data.get("stress", 0.2)), "weather": current_weather, "temp": current_temp}
                st.session_state.chat_log.insert(0, record); st.session_state.last_metrics = record
            except: pass

        # 核心布局 [4:6 比例]
        col_v, col_i = st.columns([4, 6])
        with col_v:
            st.subheader("📸 生物特征采集")
            components.html("""<div class="video-container"><video id="v" autoplay playsinline></video></div>
                <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>""", height=350)
            st.session_state.face_log.append(random.choice(["专注", "平和"]))
        with col_i:
            st.subheader("📊 实时推演")
            cur = st.session_state.last_metrics
            st.markdown(f"""<div class='status-card'>
                <small style='color:#888'>基于环境 {cur.get('weather')} 的分析：</small>
                <h2 style='color:#1A237E; margin: 10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic;'>"{cur.get('message')}"</div>
            </div>""", unsafe_allow_html=True)
            if st.button("📈 进入大数据分析看板", use_container_width=True):
                st.session_state.current_page = "stats"; st.rerun()

    elif st.session_state.current_page == "stats":
        st.title("📊 情感与环境大数据分析")
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
            st.write("### 📉 情绪走势图")
            st.line_chart(df.set_index("time")[["happiness", "stress"]])
            
            st.write("### 📑 历史详细记录（含地理环境）")
            st.dataframe(df[["time", "label", "weather", "temp", "happiness", "message"]], use_container_width=True, 
                column_config={"happiness": st.column_config.ProgressColumn("愉悦度", min_value=0, max_value=1), "message": "深度建议"})
        else:
            st.warning("数据收集中...")
        st.button("⬅️ 返回主控台", on_click=lambda: st.session_state.update({"current_page":"main"}))框架不变，只是添加手势功能
