import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 页面配置与样式 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 注入动态封面和全局 UI 样式
st.markdown("""
    <style>
    .stApp { background: #0a1118; }
    /* 动态封面样式 */
    #loading-cover {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(circle at center, #1a2a44 0%, #0a1118 100%);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        z-index: 9999; transition: opacity 1s ease;
    }
    .scanner-line {
        width: 300px; height: 2px; background: #5C6BC0;
        box-shadow: 0 0 15px #5C6BC0; animation: scan 2s ease-in-out infinite;
    }
    @keyframes scan { 0%, 100% { transform: translateY(-50px); } 50% { transform: translateY(50px); } }
    .status-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(92,107,192,0.3);
        padding: 20px; border-radius: 15px; color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 状态初始化 ---
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "正在获取...", "temp": "25.0"}
if "booted" not in st.session_state: st.session_state.booted = False

# --- 3. 动态封面逻辑 ---
if not st.session_state.booted:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("""
            <div id="loading-cover">
                <div class="scanner-line"></div>
                <h2 style="color: #5C6BC0; font-family: monospace; margin-top: 20px;">SYSTEM INITIALIZING...</h2>
                <p style="color: #444;">Connecting to Vision Sensors & GPS</p>
            </div>
        """, unsafe_allow_html=True)
        # 强制获取定位，防止“初始化”卡死
        try:
            geo = requests.get("https://ipapi.co/json/", timeout=3).json()
            st.session_state.env_data = {"city": geo.get("city", "上海"), "temp": "18.0"}
        except:
            st.session_state.env_data = {"city": "未知地区", "temp": "20.0"}
        time.sleep(2.5) # 展示封面时间
    st.session_state.booted = True
    placeholder.empty()

# --- 4. 主页面逻辑 ---
if st.session_state.current_page == "main":
    # 顶部数据栏
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🎭 Emo-Bot 视觉监测终端")
    with t2: st.markdown(f"""
        <div class="status-card">
            📍 {st.session_state.env_data['city']}<br>🌡️ {st.session_state.env_data['temp']}°C
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    col_left, col_right = st.columns([1.4, 0.6])

    with col_left:
        st.subheader("📸 实时手势节点追踪")
        
        # 核心 JS：负责 21 个红点渲染和比 ✌️ 跳转
        components.html("""
            <div id="container" style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:15px; border:4px solid #333; overflow:hidden;">
                <video id="webcam" style="position:absolute; width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="overlay" style="position:absolute; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                <div id="node-info" style="position:absolute; top:10px; right:10px; color:#0F0; font-family:monospace; font-size:12px; background:rgba(0,0,0,0.5); padding:5px;">Nodes: Searching...</div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>

            <script>
                const video = document.getElementById('webcam');
                const canvas = document.getElementById('overlay');
                const ctx = canvas.getContext('2d');
                const info = document.getElementById('node-info');

                function onResults(results) {
                    ctx.save();
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
                        info.innerText = "Nodes: Active (21 Points)";
                        for (const landmarks of results.multiHandLandmarks) {
                            // 绘制 21 个关键点连接线
                            drawConnectors(ctx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
                            // 绘制 21 个红色节点
                            drawLandmarks(ctx, landmarks, {color: '#FF0000', lineWidth: 1, radius: 3});
                            
                            // ✌️ 手势判定 (食指中指抬起，无名指收回)
                            const isV = landmarks[8].y < landmarks[6].y && landmarks[12].y < landmarks[10].y && landmarks[16].y > landmarks[14].y;
                            if (isV) {
                                info.innerText = "Gesture: Victory! Redirecting...";
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }
                        }
                    } else {
                        info.innerText = "Nodes: Searching...";
                    }
                    ctx.restore();
                }

                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                hands.setOptions({maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});
                hands.onResults(onResults);

                new Camera(video, {
                    onFrame: async () => {
                        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                        await hands.send({image: video});
                    }
                }).start();
            </script>
        """, height=480)

        # 此按钮被 JS 自动点击
        if st.button("📈 生成深度分析看板", type="primary", use_container_width=True):
            client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
            try:
                prompt = f"分析用户面部：当前地点{st.session_state.env_data['city']}，气温{st.session_state.env_data['temp']}°C。给出一个10字内表情分析和生活建议。JSON:{{'label':'表情状态','text':'建议内容'}}"
                response = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
                res_data = json.loads(response.choices[0].message.content)
                st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **res_data})
                st.session_state.current_page = "stats"
                st.rerun()
            except:
                st.error("AI 分析暂时离线")

    with col_right:
        st.subheader("📊 即时感知结论")
        if st.session_state.chat_log:
            latest = st.session_state.chat_log[-1]
            st.markdown(f"""
                <div style="background:#1a2a44; padding:20px; border-radius:15px; border-left:5px solid #5C6BC0;">
                    <h3 style="color:#5C6BC0;">{latest['label']}</h3>
                    <p style="color:#ccc;">{latest['text']}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("待机中。请比 ✌️ 手势触发系统分析。")

# --- 5. 历史看板页面 ---
elif st.session_state.current_page == "stats":
    st.title("📈 历史感知档案")
    if st.button("⬅️ 返回主控台"):
        st.session_state.current_page = "main"
        st.rerun()
    
    if st.session_state.chat_log:
        st.table(pd.DataFrame(st.session_state.chat_log).iloc[::-1])
    else:
        st.write("暂无记录")
