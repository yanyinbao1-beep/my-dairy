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
st.set_page_config(page_title="Emo-Bot Gesture Pro", layout="wide", initial_sidebar_state="collapsed")

# 初始化所有变量，确保不报错
if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = None 
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "待机中", "happiness": 0.5, "weather": "正在获取...", "message": "请正对摄像头，系统准备就绪。"}

# --- 2. 动态欢迎封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .welcome-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .scanner-ring {
            width: 140px; height: 140px;
            border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0;
            border-radius: 50%; animation: spin 1s linear infinite, glow 2s ease-in-out infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 10px #5C6BC0; } 50% { box-shadow: 0 0 40px #5C6BC0; } }
        .loading-text { margin-top: 35px; color: #5C6BC0; font-family: monospace; letter-spacing: 6px; }
        </style>
        <div class="welcome-container"><div class="scanner-ring"></div><div class="loading-text">EMO-CORE LOADING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2) 
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能执行 ---
st_autorefresh(interval=10000, key="bot_heartbeat")

# 检查 Secrets
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except Exception:
    st.error("❌ 未检测到 API Key，请在 .streamlit/secrets.toml 中配置 api_key")
    st.stop()

@st.cache_data(ttl=1800)
def get_real_context():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo.get("city", "未知地区")
        w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true", timeout=5).json()
        return f"{city}", w_res['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_real_context()

# --- 4. 情绪分析引擎 ---
def analyze_emotion():
    try:
        prompt = f"当前环境：{current_city}，气温{current_temp}度。请根据监控到的平和面部特征，给出一个感性的情绪分析。必须返回JSON：{{'label':'心情好/压力大等','text':'安慰的话','happiness':0.0-1.0}}"
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={'type': 'json_object'}
        )
        res_data = json.loads(response.choices[0].message.content)
        new_record = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "label": res_data.get('label', '稳定'),
            "message": res_data.get('text', '保持呼吸，你做得很好。'),
            "happiness": float(res_data.get('happiness', 0.5)),
            "weather": current_city,
            "temp": current_temp
        }
        st.session_state.chat_log.insert(0, new_record)
        st.session_state.last_metrics = new_record
        st.session_state.start_time = datetime.now() # 重置计时
    except Exception as e:
        st.warning(f"分析请求稍有延迟，正在重新尝试... ({str(e)})")

# 如果从未分析过，或者超过60秒，执行分析
if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
    analyze_emotion()

# --- 5. UI 渲染 ---
h_val = 210 - (float(st.session_state.last_metrics.get('happiness', 0.5)) * 100)
st.markdown(f"<style>.stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s ease; }}</style>", unsafe_allow_html=True)

if st.session_state.current_page == "main":
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🤖 Emo-Bot 深度监测终端")
    with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([4, 6])
    
    with col_v:
        st.subheader("📸 视觉流与手势")
        
        components.html("""
            <div style="width:100%; max-width:460px; aspect-ratio:4/3; position:relative; background:#000; border-radius:15px; overflow:hidden;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%;"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.7});
                
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        // ✌️ 判定逻辑：食指中指伸直，其余弯曲
                        if (lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {
                            window.parent.postMessage({type: 'GOTO_STATS'}, '*');
                        }
                    }
                });
                const camera = new Camera(video, { onFrame: async () => { await hands.send({image: video}); } });
                camera.start();
            </script>
        """, height=360)
        st.caption("🖐️ 提示：对着摄像头比 ✌️ 手势可自动跳转看板")

    with col_i:
        st.subheader("📊 实时推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:20px; padding:25px; border-left:10px solid #5C6BC0; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
                <small style='color:#888'>AI 实时画像：</small>
                <h2 style='color:#1A237E; margin:10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic;'>"{cur.get('message')}"</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("📈 点击查看深度分析报告", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据分析")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log)
        
        st.line_chart(df.set_index("time")["happiness"])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("暂无历史记录，正在生成中...")
    
    if st.button("⬅️ 返回主控台", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
