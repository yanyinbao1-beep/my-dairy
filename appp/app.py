import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide")

if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "就绪", "message": "等待扫描..."}

# --- 2. 动态封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; }
        .cir { width: 60px; height: 60px; border: 5px solid #1a1f2b; border-top: 5px solid #5C6BC0; border-radius: 50%; animation: s 1s linear infinite; }
        @keyframes s { 100% { transform: rotate(360deg); } }
        </style>
        <div class="loader"><div class="cir"></div><div style="color:#5C6BC0;margin-top:20px;">SYSTEM LOADING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心引擎 ---
st_autorefresh(interval=20000, key="bot_refresh")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=3600)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return geo.get("city", "未知地区"), w['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# 实用建议 AI 逻辑
if "next_update" not in st.session_state or time.time() > st.session_state.next_update:
    try:
        p = f"你是生活助手。当前{current_city},{current_temp}度。给出状态标签和15字建议。JSON:{{'label':'状态','text':'建议','happiness':0.5}}"
        r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], response_format={'type':'json_object'})
        d = json.loads(r.choices[0].message.content)
        st.session_state.last_metrics = d
        st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M"), **d})
        st.session_state.next_update = time.time() + 60
    except: pass

# --- 4. 页面渲染 ---
if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🤖 Emo-Bot 监测站")
    with c2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([1, 1])
    
    with col_v:
        st.subheader("📸 视觉监测（含手部骨架）")
        # 增加手部骨架绘制，方便调试
        
        components.html(f"""
            <div id="box" style="position:relative; width:100%; aspect-ratio:4/3; background:#222; border-radius:10px; overflow:hidden; border: 5px solid #444;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            </div>
            <p id="msg" style="color:#666; font-size:12px; margin-top:5px;">正在初始化模型...</p>
            
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            <script>
                const v = document.getElementById('v');
                const c = document.getElementById('c');
                const ctx = c.getContext('2d');
                const msg = document.getElementById('msg');
                const box = document.getElementById('box');

                const hands = new Hands({{locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`}});
                hands.setOptions({{maxNumHands: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5}});

                hands.onResults((res) => {{
                    ctx.clearRect(0, 0, c.width, c.height);
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {{
                        msg.innerText = "检测到手部，请比 ✌️";
                        const lm = res.multiHandLandmarks[0];
                        // 绘制骨架，如果画面出现红线，说明检测成功了
                        drawConnectors(ctx, lm, HAND_CONNECTIONS, {{color: '#00FF00', lineWidth: 2}});
                        drawLandmarks(ctx, lm, {{color: '#FF0000', lineWidth: 1}});
                        
                        // ✌️ 判定
                        const isV = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                        if (isV) {{
                            box.style.borderColor = "#00FF00";
                            msg.innerText = "✌️ 捕捉成功！正在跳转...";
                            // 最终手段：改变 URL 后缀触发跳转
                            window.top.location.href = window.top.location.href.split('?')[0] + "?nav=stats";
                        }}
                    }} else {{
                        msg.innerText = "未检测到手部，请将手对准摄像头";
                    }}
                }});

                const camera = new Camera(v, {{
                    onFrame: async () => {{
                        c.width = v.videoWidth;
                        c.height = v.videoHeight;
                        await hands.send({{image: v}});
                    }}
                }});
                camera.start();
            </script>
        """, height=420)

        # 检查跳转参数
        if st.query_params.get("nav") == "stats":
            st.session_state.current_page = "stats"
            st.query_params.clear()
            st.rerun()

        if st.button("📈 手动进入看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 实时推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:12px; padding:20px; border-left:10px solid #5C6BC0; box-shadow:0 4px 10px rgba(0,0,0,0.05);">
                <p style="color:#888; margin-bottom:5px;">AI 诊断状态：</p>
                <h2 style="color:#1A237E; margin-top:0;">{cur.get('label')}</h2>
                <hr>
                <p style="color:#333; font-size:1.1rem;"><b>生活建议：</b>{cur.get('text')}</p>
            </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据表")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log)
        st.dataframe(df, use_container_width=True)
    st.button("⬅️ 返回主控制台", on_click=lambda: st.session_state.update({"current_page":"main"}))
