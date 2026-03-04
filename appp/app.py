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
st.set_page_config(page_title="Emo-Bot Vision Pro", layout="wide", initial_sidebar_state="collapsed")

if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "扫描中", "happiness": 0.5, "stress": 0.2, "emotion": "正在对焦",
        "weather": "载入中", "temp": "--", "message": "正在锁定生物特征中心..."
    }

# --- 2. 启动动画 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #050505; }
        .loader-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; }
        .scanner {
            width: 200px; height: 2px; background: #5C6BC0;
            box-shadow: 0 0 15px #5C6BC0; animation: scan 2s infinite;
        }
        @keyframes scan { 0% { transform: translateY(-50px); } 50% { transform: translateY(50px); } 100% { transform: translateY(-50px); } }
        .text { color: #5C6BC0; margin-top: 30px; letter-spacing: 3px; font-family: monospace; }
        </style>
        <div class="loader-box"><div class="scanner"></div><div class="text">BIOMETRIC SCANNING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(1.5); st.session_state.welcome_finished = True; st.rerun()

# --- 3. 核心功能 ---
else:
    st_autorefresh(interval=10000, key="vision_heartbeat")
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

    @st.cache_data(ttl=1800)
    def get_context():
        try:
            res = requests.get("http://ip-api.com/json/", timeout=2).json()
            return f"{res.get('city')} | 监测中", 24.0
        except: return "未知区域", 25.0

    current_weather, current_temp = get_context()

    # 动态样式：增加人物对焦框视觉
    m = st.session_state.last_metrics
    h_val = 210 - (float(m.get('happiness', 0.5)) * 120)
    st.markdown(f"""
        <style>
        .stApp {{ background: hsl({h_val}, 10%, 95%); transition: 2s; }}
        .video-wrapper {{
            position: relative; width: 100%; padding-top: 75%; /* 4:3 */
            border: 4px solid #1a1a1a; border-radius: 24px; overflow: hidden;
            background: #000;
        }}
        /* 强制画面居中并镜像 */
        video {{ 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            object-fit: cover; transform: scaleX(-1); 
        }}
        /* 人物对焦辅助框 */
        .focus-box {{
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 60%; height: 70%; border: 1px solid rgba(255,255,255,0.3);
            border-radius: 40% 40% 50% 50%; pointer-events: none;
        }}
        .status-card {{
            background: white; border-radius: 24px; padding: 25px;
            border-bottom: 8px solid hsl({h_val}, 60%, 50%);
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        }}
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.current_page == "main":
        col_v, col_i = st.columns([4.5, 5.5])

        with col_v:
            st.markdown("### 👁️ 生物特征识别")
            components.html("""
                <div class="video-wrapper">
                    <video id="webcam" autoplay playsinline></video>
                    <div class="focus-box"></div>
                </div>
                <script>
                const v = document.getElementById('webcam');
                navigator.mediaDevices.getUserMedia({
                    video: { aspectRatio: 1.333, facingMode: "user" }
                }).then(s => { v.srcObject = s; });
                </script>
            """, height=420)
            st.caption("请确保面部位于对焦框中心 | 实时渲染中")

        with col_i:
            # AI 逻辑升级：模拟情绪识别
            elapsed = (datetime.now() - st.session_state.start_time).seconds
            if elapsed >= 60 or not st.session_state.chat_log:
                st.session_state.start_time = datetime.now()
                try:
                    # 模拟视觉特征描述（由于DeepSeek不直接看图，我们通过Prompt引导它生成更具体的模拟分析）
                    prompt = f"""
                    [系统指令] 你正在分析摄像头实时画面。
                    [当前环境] {current_weather}
                    [识别目标] 位于对焦框中心的成年个体。
                    请随机模拟检测到的一种具体情绪（如：深思、隐秘的喜悦、职业性倦怠、宁静、灵感迸发）。
                    返回JSON:
                    {{
                        "emotion": "具体情绪词",
                        "label": "4字状态总结",
                        "text": "一句针对该特定情绪的深度洞察(30字内)",
                        "happiness": 0.0-1.0, "stress": 0.0-1.0
                    }}
                    """
                    resp = client.chat.completions.create(
                        model="deepseek-chat", messages=[{"role": "user", "content": prompt}],
                        response_format={'type': 'json_object'}, temperature=1.1
                    )
                    data = json.loads(resp.choices[0].message.content)
                    record = {
                        "time": datetime.now().strftime("%H:%M"), "label": data.get("label"),
                        "emotion": data.get("emotion"), "message": data.get("text"),
                        "happiness": float(data.get("happiness")), "stress": float(data.get("stress")),
                        "weather": current_weather, "temp": current_temp
                    }
                    st.session_state.chat_log.insert(0, record)
                    st.session_state.last_metrics = record
                except: pass

            cur = st.session_state.last_metrics
            st.markdown(f"""
                <div class='status-card'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#5C6BC0; font-weight:bold;'>ID: SUBJECT_01</span>
                        <span style='color:#888;'>{cur.get('time')}</span>
                    </div>
                    <h1 style='margin:10px 0; color:#1a1a1a;'>{cur.get('label')}</h1>
                    <div style='background:#f8f9fa; border-radius:12px; padding:15px; margin:15px 0;'>
                        <b style='color:#5C6BC0;'>检测到具体情绪：</b> {cur.get('emotion')}
                    </div>
                    <p style='font-size:1.1rem; line-height:1.6; color:#444;'>“{cur.get('message')}”</p>
                    <hr>
                    <div style='display:grid; grid-template-columns: 1fr 1fr; gap:20px; text-align:center;'>
                        <div><small>愉悦指数</small><br><b>{int(cur.get('happiness')*100)}%</b></div>
                        <div><small>压力负荷</small><br><b>{int(cur.get('stress')*100)}%</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📊 查看完整情绪轨迹", use_container_width=True):
                st.session_state.current_page = "stats"; st.rerun()

    elif st.session_state.current_page == "stats":
        st.title("📊 情绪大数据看板")
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log)
            st.line_chart(df.set_index("time")[["happiness", "stress"]])
            st.table(df[["time", "emotion", "label", "message"]])
        st.button("返回", on_click=lambda: st.session_state.update({"current_page":"main"}))
