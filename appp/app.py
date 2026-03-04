import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 初始化状态
for key, val in {
    "welcome_finished": False, 
    "current_page": "main", 
    "chat_log": [], 
    "last_metrics": {"label": "感知中", "text": "正在同步环境..."}
}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 2. 封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; color: #5C6BC0; font-family: monospace; }
        .ring { width: 50px; height: 50px; border: 3px solid #1a1f2b; border-top: 3px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        </style>
        <div class="loader"><div class="ring"></div>CONNECTING SENSORS...</div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 强力定位引擎 (解决定位初始化不动) ---
@st.cache_data(ttl=600)
def fetch_env():
    # 尝试三个不同的定位源，防止卡死
    sources = ["https://ipapi.co/json/", "https://ip-api.com/json/", "https://freeipapi.com/api/json"]
    city, temp = "未知地区", 20.0
    for src in sources:
        try:
            res = requests.get(src, timeout=3).json()
            city = res.get("city") or res.get("cityName") or city
            lat = res.get("latitude") or res.get("lat") or 39.9
            lon = res.get("longitude") or res.get("lon") or 116.4
            w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=3).json()
            temp = w['current_weather']['temperature']
            break # 只要有一个成功就跳出
        except: continue
    return city, temp

current_city, current_temp = fetch_env()

# --- 4. AI 分析逻辑 (表情分析) ---
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

def run_ai_analysis():
    try:
        prompt = f"分析当前{current_city}({current_temp}度)下的用户表情。JSON格式返回:{{'label':'专注/欣喜/疲惫','text':'一句15字建议','happiness':0.5}}"
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.last_metrics = data
        st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M"), **data})
    except: pass

st_autorefresh(interval=30000, key="ai_refresh")

# --- 5. 页面路由 ---
if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🎭 Emo-Bot 视觉监测")
    with c2: st.metric("📍 实时位置", f"{current_city}", f"{current_temp}℃")

    col_v, col_i = st.columns([1.2, 0.8])
    with col_v:
        st.subheader("📸 节点追踪 (比 ✌️ 进入看板)")
        
        # 使用 Template 字符串避免大括号转义报错
        js_code = """
        <div id="box" style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:12px; border:4px solid #333;">
            <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
            <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            <div id="log" style="position:absolute; top:10px; right:10px; color:#0F0; font-family:monospace; font-size:10px; background:rgba(0,0,0,0.5); padding:4px;">Ready</div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
        <script>
            const v = document.getElementById('v');
            const c = document.getElementById('c');
            const ctx = c.getContext('2d');
            const log = document.getElementById('log');

            const hands = new Hands({locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`});
            hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.5});

            hands.onResults((res) => {
                ctx.clearRect(0, 0, c.width, c.height);
                if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                    log.innerText = "Tracking...";
                    for (const lm of res.multiHandLandmarks) {
                        drawConnectors(ctx, lm, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
                        drawLandmarks(ctx, lm, {color: '#FF0000', lineWidth: 1, radius: 2});
                        // ✌️ 判定
                        if (lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {
                            log.innerText = "✌️ Triggered!";
                            window.parent.document.querySelector('button[kind="primary"]').click();
                        }
                    }
                }
            });

            new Camera(v, {
                onFrame: async () => {
                    c.width = v.videoWidth; c.height = v.videoHeight;
                    await hands.send({image: v});
                }
            }).start().catch(() => { log.innerText = "Camera Error"; });
        </script>
        """
        components.html(js_code, height=400)
        
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            run_ai_analysis()
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 表情分析结论")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:20px; border-left:10px solid #5C6BC0; box-shadow:0 5px 15px rgba(0,0,0,0.05);">
                <p style="color:#888; margin-bottom:5px;">AI 实时诊断：</p>
                <h2 style="color:#1A237E; margin-top:0;">{cur.get('label')}</h2>
                <hr>
                <p style="color:#333;"><b>生活贴士：</b><br>{cur.get('text')}</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 刷新地点与建议"):
            st.cache_data.clear()
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 历史数据")
    if st.button("⬅️ 返回主控"):
        st.session_state.current_page = "main"
        st.rerun()
    if st.session_state.chat_log:
        st.dataframe(pd.DataFrame(st.session_state.chat_log), use_container_width=True)
