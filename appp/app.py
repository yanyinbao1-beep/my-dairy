import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础页面设置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 变量初始化
if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = None
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "就绪", "happiness": 0.5, "message": "等待系统扫描..."}

# --- 2. 动态封面 (保留) ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 80px; height: 80px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .text { margin-top: 20px; color: #5C6BC0; font-family: monospace; letter-spacing: 3px; }
        </style>
        <div class="loader-box"><div class="ring"></div><div class="text">BOOTING SYSTEM...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心引擎与数据 ---
st_autorefresh(interval=15000, key="heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=1800)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo.get("city", "未知地区")
        w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return city, w_res['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# 实用版 AI 提示词
def analyze_simple():
    try:
        prompt = f"你是一个情绪分析助手。当前城市：{current_city}，气温：{current_temp}℃。请结合环境给出客观状态分析和20字以内的简单建议。必须返回JSON：{{'label':'专注/放松等','text':'建议内容','happiness':0.5}}"
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
        data = json.loads(resp.choices[0].message.content)
        record = {"time": datetime.now().strftime("%H:%M:%S"), "label": data['label'], "message": data['text'], "happiness": data['happiness'], "weather": current_city, "temp": current_temp}
        st.session_state.chat_log.insert(0, record)
        st.session_state.last_metrics = record
        st.session_state.start_time = datetime.now()
    except: pass

if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
    analyze_simple()

# --- 4. 界面渲染 ---
if st.session_state.current_page == "main":
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🤖 Emo-Bot 监测站")
    with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([4.5, 5.5])
    
    with col_v:
        st.subheader("📸 实时监测")
        
        # 强制跳转逻辑：直接监听 URL 参数变化
        if st.query_params.get("page") == "stats":
            st.session_state.current_page = "stats"
            st.query_params.clear()
            st.rerun()

        components.html("""
            <div id="container" style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border:4px solid transparent; border-radius:12px; overflow:hidden; transition: 0.3s;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <div id="stat" style="position:absolute; top:8px; left:8px; color:#00FF00; background:rgba(0,0,0,0.6); padding:4px 8px; border-radius:4px; font-size:11px;">比 ✌️ 跳转分析</div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const stat = document.getElementById('stat');
                const container = document.getElementById('container');
                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});
                
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        // 判定 ✌️：食指(8)和中指(12)尖端显著高于指根(6, 10)，且无名指(16)收起
                        const isVictory = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                        if (isVictory) {
                            container.style.borderColor = "#FF4B4B";
                            stat.innerText = "捕捉成功！正在切换...";
                            // 物理级跳转：强制刷新并携带参数
                            window.top.location.href = window.top.location.pathname + "?page=stats";
                        }
                    }
                });
                const camera = new Camera(video, {onFrame: async () => { await hands.send({image: video}); }, width: 480, height: 360});
                camera.start();
            </script>
        """, height=380)
        
        if st.button("📈 手动进入看板 (若手势失效请点此)", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 监测结果")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:20px; border-left:8px solid #5C6BC0; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
                <p style='color:#666; font-size:0.9rem; margin-bottom:5px;'>实时画像：</p>
                <h3 style='color:#1A237E; margin-top:0;'>{cur.get('label')}</h3>
                <hr style='border:0; border-top:1px solid #eee;'>
                <p style='color:#333;'><b>建议：</b>{cur.get('message')}</p>
            </div>
        """, unsafe_allow_html=True)
        st.caption("提示：请在光线充足的地方比出 ✌️，手心正对摄像头。")

elif st.session_state.current_page == "stats":
    st.title("📊 历史分析中心")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.line_chart(df.set_index("time")["happiness"])
        st.dataframe(df[["time", "label", "weather", "temp", "message"]], use_container_width=True)
    
    if st.button("⬅️ 返回主控制台", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
