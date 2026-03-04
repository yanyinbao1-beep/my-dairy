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
    st.session_state.last_metrics = {"label": "初始化", "text": "正在同步面部数据..."}

# --- 2. 动态加载封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 60px; height: 60px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        </style>
        <div class="loader"><div class="ring"></div><div style="color:#5C6BC0;margin-top:20px;font-family:monospace;">FACIAL SCANNER & GESTURE NODES LOADING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心引擎 (API & 环境) ---
st_autorefresh(interval=15000, key="bot_heartbeat")
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

def analyze_emotion():
    try:
        prompt = f"你是一个面部分析助手。当前环境：{current_city}，{current_temp}℃。请根据用户此刻的表情给出状态标签和15字建议。JSON:{{'label':'状态','text':'建议','happiness':0.5}}"
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.last_metrics = data
        st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M"), **data})
        st.session_state.start_time = time.time()
    except: pass

if "start_time" not in st.session_state or (time.time() - st.session_state.start_time) > 60:
    analyze_emotion()

# --- 4. 界面渲染 ---

# 【主页：比 ✌️ 跳转】
if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🎭 Emo-Bot 面部监测站")
    with c2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([1, 1])
    with col_v:
        st.subheader("📸 21节点监测 (比 ✌️ 进入)")
        
        components.html("""
            <div style="position:relative; width:100%; aspect-ratio:4/3; background:#222; border-radius:12px; overflow:hidden; border: 4px solid #444;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const canvas = document.getElementById('c');
                const ctx = canvas.getContext('2d');
                const hands = new Hands({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`});
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.6});
                hands.onResults((res) => {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        for (const lm of res.multiHandLandmarks) {
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
                            drawLandmarks(ctx, lm, {color: '#FF0000', lineWidth: 1, radius: 2});
                            const isV = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                            if (isV) { window.parent.document.querySelector('button[kind="primary"]').click(); }
                        }
                    }
                });
                new Camera(video, {onFrame: async () => { 
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                    await hands.send({image: video}); 
                }}).start();
            </script>
        """, height=380)
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"; st.rerun()

    with col_i:
        st.subheader("📊 表情分析结论")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:12px; padding:20px; border-left:10px solid #5C6BC0; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
                <p style="color:#888;">AI 实时面部分析：</p>
                <h2 style="color:#1A237E; margin-top:0;">{cur.get('label')}</h2>
                <hr>
                <p style="color:#333; font-size:1.1rem;"><b>建议：</b>{cur.get('text')}</p>
            </div>
        """, unsafe_allow_html=True)

# 【分析页：比 👍 返回】
elif st.session_state.current_page == "stats":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("📈 历史趋势看板")
    with c2: st.success("👍 竖大拇指：返回主页")

    col_v, col_d = st.columns([1, 1])
    with col_v:
        components.html("""
            <div style="position:relative; width:100%; aspect-ratio:16/9; background:#222; border-radius:10px; overflow:hidden; border: 4px solid #5C6BC0;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const canvas = document.getElementById('c');
                const ctx = canvas.getContext('2d');
                const hands = new Hands({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`});
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.6});
                hands.onResults((res) => {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        drawConnectors(ctx, lm, HAND_CONNECTIONS, {color: '#5C6BC0', lineWidth: 2});
                        // 👍 判定逻辑：大拇指尖(4)高于大拇指根(2)，且高于食指尖(8)
                        const isThumbUp = lm[4].y < lm[2].y && lm[4].y < lm[8].y;
                        if (isThumbUp) { window.parent.document.evaluate("//button[contains(., '返回主控')]", window.parent.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click(); }
                    }
                });
                new Camera(video, {onFrame: async () => { 
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                    await hands.send({image: video}); 
                }}).start();
            </script>
        """, height=250)
        if st.button("⬅️ 返回主控", use_container_width=True):
            st.session_state.current_page = "main"; st.rerun()

    with col_d:
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log)
            st.line_chart(df.set_index("time")["happiness"])
            st.dataframe(df[["time", "label", "text"]], use_container_width=True)
