import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "待机", "text": "等待扫描环境..."}

# --- 2. 动态加载封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 60px; height: 60px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        </style>
        <div class="loader"><div class="ring"></div><div style="color:#5C6BC0;margin-top:20px;font-family:monospace;">SYSTEM LOADING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心引擎 (API & 环境) ---
st_autorefresh(interval=20000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=3600)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo.get("city", "未知地区")
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return city, w['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# 简洁版分析逻辑
if "next_update" not in st.session_state or time.time() > st.session_state.next_update:
    try:
        prompt = f"你是助手。当前{current_city},{current_temp}度。给出状态标签和15字内生活建议。JSON:{{'label':'状态','text':'建议','happiness':0.5}}"
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.last_metrics = data
        st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M"), **data})
        st.session_state.next_update = time.time() + 60
    except: pass

# --- 4. 页面路由渲染 ---
if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🤖 Emo-Bot 监测站")
    with c2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([1, 1])
    
    with col_v:
        st.subheader("📸 视觉监测 (比 ✌️ 跳转)")
        
        # 修复 NameError 的 HTML 组件
        
        components.html("""
            <div id="video-container" style="position:relative; width:100%; aspect-ratio:4/3; background:#222; border-radius:10px; overflow:hidden; border: 4px solid #444;">
                <video id="input_video" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="output_canvas" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                <div id="status-tag" style="position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.7); color:#00FF00; padding:4px 8px; border-radius:4px; font-size:12px;">模型加载中...</div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            
            <script>
                const videoElement = document.getElementById('input_video');
                const canvasElement = document.getElementById('output_canvas');
                const canvasCtx = canvasElement.getContext('2d');
                const statusTag = document.getElementById('status-tag');
                const container = document.getElementById('video-container');

                function onResults(results) {
                    canvasCtx.save();
                    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
                        statusTag.innerText = "已检测到手部";
                        for (const landmarks of results.multiHandLandmarks) {
                            drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
                            drawLandmarks(canvasCtx, landmarks, {color: '#FF0000', lineWidth: 1});
                            
                            // ✌️ 判定逻辑
                            const isV = landmarks[8].y < landmarks[6].y && landmarks[12].y < landmarks[10].y && landmarks[16].y > landmarks[14].y;
                            if (isV) {
                                statusTag.innerText = "✌️ 捕捉成功！跳转中...";
                                container.style.borderColor = "#00FF00";
                                // 触发 Streamlit 按钮点击
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }
                        }
                    } else {
                        statusTag.innerText = "请将手对准摄像头";
                    }
                    canvasCtx.restore();
                }

                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                hands.setOptions({ maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
                hands.onResults(onResults);

                const camera = new Camera(videoElement, {
                    onFrame: async () => {
                        canvasElement.width = videoElement.videoWidth;
                        canvasElement.height = videoElement.videoHeight;
                        await hands.send({image: videoElement});
                    }
                });
                camera.start();
            </script>
        """, height=400)

        # 核心跳转按钮 (将被 JS 自动点击)
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 实时状态")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:12px; padding:20px; border-left:10px solid #5C6BC0; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
                <p style="color:#888; margin-bottom:5px;">AI 分析结论：</p>
                <h2 style="color:#1A237E; margin-top:0;">{cur.get('label')}</h2>
                <hr>
                <p style="color:#333; font-size:1.1rem;"><b>生活小贴士：</b>{cur.get('text')}</p>
            </div>
        """, unsafe_allow_html=True)
        st.caption(f"提示：当前 {current_city} 气温为 {current_temp}℃，建议已根据环境优化。")

elif st.session_state.current_page == "stats":
    st.title("📊 历史记录看板")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log)
        st.dataframe(df, use_container_width=True)
    
    if st.button("⬅️ 返回主控制台", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
