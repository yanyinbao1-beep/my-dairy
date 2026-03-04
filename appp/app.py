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
    st.session_state.last_metrics = {"label": "初始化", "text": "系统启动中..."}

# --- 2. 动态加载封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 60px; height: 60px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        </style>
        <div class="loader"><div class="ring"></div><div style="color:#5C6BC0;margin-top:20px;font-family:monospace;">GPS & SENSOR INITIALIZING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心引擎 (实时定位与 AI) ---
st_autorefresh(interval=20000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# 强制刷新地理位置 (去掉 cache)
def get_realtime_env():
    try:
        # 使用更稳定的 IP 定位 API
        geo = requests.get("https://ipapi.co/json/", timeout=5).json()
        city = geo.get("city", "未知城市")
        lat, lon = geo.get("latitude", 39.9), geo.get("longitude", 116.4)
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
        return city, w['current_weather']['temperature']
    except: return "定位获取中", 25.0

current_city, current_temp = get_realtime_env()

def analyze_face_logic():
    try:
        prompt = f"你是助手。当前：{current_city}，{current_temp}℃。分析表情给标签和15字建议。JSON:{{'label':'专注/放松','text':'建议','happiness':0.5}}"
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.last_metrics = data
        st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), **data})
    except: pass

# --- 4. 界面渲染 ---

if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🎭 Emo-Bot 视觉监测终端")
    with c2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([1.2, 0.8])
    with col_v:
        st.subheader("📸 实时节点追踪 (比 ✌️ 进入)")
        
        # 增加脚本加载检测逻辑
        components.html("""
            <div id="container" style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:12px; border: 4px solid #333;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                <div id="debug" style="position:absolute; bottom:10px; left:10px; color:#00FF00; background:rgba(0,0,0,0.7); padding:5px; font-family:monospace; font-size:12px;">系统准备中...</div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            
            <script>
                const v = document.getElementById('v');
                const c = document.getElementById('c');
                const ctx = c.getContext('2d');
                const debug = document.getElementById('debug');

                const hands = new Hands({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`});
                hands.setOptions({maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});

                hands.onResults((res) => {
                    ctx.clearRect(0, 0, c.width, c.height);
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        debug.innerText = "状态: 节点已连接";
                        for (const lm of res.multiHandLandmarks) {
                            // 绘制骨架线和红点
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 3});
                            drawLandmarks(ctx, lm, {color: '#FF0000', lineWidth: 1, radius: 3});
                            
                            // ✌️ 跳转检测
                            const isV = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                            if (isV) {
                                debug.innerText = "状态: ✌️ 跳转触发！";
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }
                        }
                    } else {
                        debug.innerText = "状态: 等待手部切入画面...";
                    }
                });

                new Camera(v, {
                    onFrame: async () => {
                        c.width = v.videoWidth; c.height = v.videoHeight;
                        await hands.send({image: v});
                    }
                }).start().then(() => { debug.innerText = "状态: 摄像头已授权"; });
            </script>
        """, height=420)
        
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            analyze_face_logic() # 跳转时触发一次AI分析
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 监测画像")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:25px; border-left:10px solid #5C6BC0; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
                <p style="color:#888; margin-bottom:10px;">表情映射状态：</p>
                <h2 style="color:#1A237E; margin-top:0;">{cur.get('label')}</h2>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                <p style="color:#333; font-size:1.1rem; line-height:1.6;"><b>实时建议：</b>{cur.get('text')}</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 手动刷新天气与分析"):
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 历史数据看板")
    st.info("👍 竖起大拇指返回主页（或点击下方按钮）")
    
    col_v, col_d = st.columns([1, 1])
    with col_v:
        components.html("""
            <div id="v-box" style="position:relative; width:100%; aspect-ratio:16/9; background:#222; border-radius:10px; overflow:hidden; border: 4px solid #5C6BC0;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const v = document.getElementById('v');
                const hands = new Hands({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`});
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.6});
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        const isThumbUp = lm[4].y < lm[2].y && lm[4].y < lm[8].y;
                        if (isThumbUp) {
                            window.parent.document.evaluate("//button[contains(., '返回主控')]", window.parent.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click();
                        }
                    }
                });
                new Camera(v, {onFrame: async () => { await hands.send({image: v}); }}).start();
            </script>
        """, height=260)
        if st.button("⬅️ 返回主控", use_container_width=True):
            st.session_state.current_page = "main"; st.rerun()

    with col_d:
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log)
            st.line_chart(df.set_index("time")["happiness"])
            st.dataframe(df, use_container_width=True)
