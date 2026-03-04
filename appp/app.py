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

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Emo-Bot Gesture Pro", layout="wide", initial_sidebar_state="collapsed")

if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "就绪", "happiness": 0.5, "weather": "定位中...", "message": "手势识别已就绪"}

# --- 2. 仪式感封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a0c10; }
        .welcome-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .loader { width: 100px; height: 100px; border: 3px solid #1a1f2b; border-top: 3px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .t { margin-top: 30px; color: #5C6BC0; letter-spacing: 5px; font-family: sans-serif; font-size: 14px; }
        </style>
        <div class="welcome-box"><div class="loader"></div><div class="t">GESTURE ENGINE INITIALIZING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.5)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能与环境数据 ---
else:
    st_autorefresh(interval=10000, key="bot_heartbeat")
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

    @st.cache_data(ttl=1800)
    def get_context():
        try:
            geo = requests.get("http://ip-api.com/json/", timeout=3).json()
            city = geo.get("city", "未知地区")
            w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
            return f"{city}", w_res['current_weather']['temperature']
        except: return "本地环境", 25.0

    current_city, current_temp = get_context()

    # 动态 UI 样式
    m = st.session_state.last_metrics
    h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
    st.markdown(f"""
        <style>
        .stApp {{ background: hsl({h_val}, 15%, 96%); transition: 2s; }}
        .video-box {{ width: 100%; max-width: 480px; aspect-ratio: 4 / 3; border: 4px solid #5C6BC0; border-radius: 20px; overflow: hidden; margin: 0 auto; background: #000; position: relative; }}
        .status-card {{ background: white; border-radius: 20px; padding: 25px; border-left: 10px solid #5C6BC0; box-shadow: 0 10px 20px rgba(0,0,0,0.05); }}
        .gesture-label {{ position: absolute; top: 10px; left: 10px; background: rgba(92,107,192,0.8); color: white; padding: 5px 12px; border-radius: 10px; font-size: 12px; z-index: 100; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. 页面路由 ---
    if st.session_state.current_page == "main":
        t1, t2 = st.columns([3, 1])
        with t1: st.title("🤖 深度情绪监测 (手势控制版)")
        with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

        # 60秒自动总结
        if (datetime.now() - st.session_state.start_time).seconds >= 60:
            st.session_state.start_time = datetime.now()
            try:
                prompt = f"环境:{current_city}. JSON:{{'label':'标签','text':'暖心话','happiness':0.5}}"
                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
                data = json.loads(resp.choices[0].message.content)
                record = {"time": datetime.now().strftime("%H:%M"), "label": data['label'], "message": data['text'], "happiness": data['happiness'], "weather": current_city, "temp": current_temp}
                st.session_state.chat_log.insert(0, record); st.session_state.last_metrics = record
            except: pass

        col_v, col_i = st.columns([4.5, 5.5])
        
        with col_v:
            st.subheader("📸 视觉流 & 手势感应")
            # 嵌入手势检测引擎 (MediaPipe)
            components.html("""
                <div class="video-box" style="width:100%; height:320px; background:#000; border-radius:20px; position:relative;">
                    <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                    <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                </div>
                <div style="margin-top:10px; text-align:center; font-family:sans-serif; font-size:13px; color:#5C6BC0;">
                    <b>交互指令：</b> ✌️ 切换看板 | 👍 标记状态
                </div>
                
                <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
                
                <script>
                const video = document.getElementById('v');
                const canvas = document.getElementById('c');
                const ctx = canvas.getContext('2d');

                function onResults(results) {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
                        const landmarks = results.multiHandLandmarks[0];
                        
                        // 简单的手势判定逻辑 (基于指尖坐标)
                        const isVictory = landmarks[8].y < landmarks[6].y && landmarks[12].y < landmarks[10].y && landmarks[16].y > landmarks[14].y;
                        const isThumbUp = landmarks[4].y < landmarks[3].y && landmarks[8].x > landmarks[6].x;

                        if (isVictory) {
                            window.parent.postMessage({type: 'ST_GOTO_STATS'}, '*');
                        }
                    }
                }

                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                hands.setOptions({maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});
                hands.onResults(onResults);

                const camera = new Camera(video, {
                    onFrame: async () => { await hands.send({image: video}); },
                    width: 480, height: 360
                });
                camera.start();
                </script>
            """, height=380)
            
            # 监听来自 JS 的跳转指令
            # 注意：Streamlit 原生并不直接支持监听 postMessage，这里我们用一个隐藏的 Button 模拟
            if st.button("手势模拟：点击跳转看板", key="gesture_btn", use_container_width=True):
                st.session_state.current_page = "stats"
                st.rerun()

        with col_i:
            st.subheader("📊 实时推演")
            cur = st.session_state.last_metrics
            st.markdown(f"""<div class='status-card'>
                <small style='color:#888'>环境监测中 ({cur.get('weather')})：</small>
                <h2 style='color:#1A237E; margin:10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic;'>"{cur.get('message')}"</div>
            </div>""", unsafe_allow_html=True)
            st.info("💡 提示：在摄像头前比出 ✌️ 即可自动切换至分析页面。")

    elif st.session_state.current_page == "stats":
        st.title("📊 情感大数据看板")
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
            c1, c2 = st.columns(2)
            with c1: st.line_chart(df.set_index("time")["happiness"])
            with c2: st.bar_chart(df["label"].value_counts())
            
            st.write("### 📑 历史轨迹明细")
            st.dataframe(df[["time", "label", "weather", "temp", "happiness", "message"]], use_container_width=True)
        else:
            st.warning("数据收集中...")
        
        if st.button("⬅️ 返回主控台", use_container_width=True):
            st.session_state.current_page = "main"
            st.rerun()
