import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 基础页面设置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 初始化 Session 状态
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "正在定位...", "temp": "25.0"}
if "ai_result" not in st.session_state: st.session_state.ai_result = {"label": "等待扫描", "text": "请面向摄像头"}

# --- 2. 强制地理位置获取 (Python备用方案) ---
def get_env_python():
    try:
        res = requests.get("https://ipapi.co/json/", timeout=2).json()
        st.session_state.env_data = {"city": res.get("city", "北京"), "temp": "15.0"}
    except:
        st.session_state.env_data = {"city": "北京", "temp": "15.0"}

if st.session_state.env_data["city"] == "正在定位...":
    get_env_python()

# --- 3. 页面逻辑 ---
if st.session_state.current_page == "main":
    # 顶部状态栏
    st.markdown(f"### 📍 {st.session_state.env_data['city']} | 🌡️ {st.session_state.env_data['temp']}°C")
    
    col_v, col_i = st.columns([1.3, 0.7])
    
    with col_v:
        st.subheader("📸 21节点实时监测")
        # 这里的 JS 代码包含了手势连接线和红点的绘制逻辑
                components.html("""
            <div id="wrapper" style="position:relative; width:100%; aspect-ratio:4/3; background:#111; border-radius:15px; border:4px solid #333; overflow:hidden;">
                <video id="input_video" style="position:absolute; width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="output_canvas" style="position:absolute; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                <div id="ui" style="position:absolute; top:10px; left:10px; color:#0F0; font-family:monospace; background:rgba(0,0,0,0.6); padding:5px; border-radius:5px;">System Active</div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>

            <script>
                const videoElement = document.getElementById('input_video');
                const canvasElement = document.getElementById('output_canvas');
                const canvasCtx = canvasElement.getContext('2d');
                const ui = document.getElementById('ui');

                function onResults(results) {
                    canvasCtx.save();
                    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                    
                    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
                        ui.innerText = "Tracking Hand Nodes...";
                        for (const landmarks of results.multiHandLandmarks) {
                            // 关键点连线 (绿线)
                            drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 3});
                            // 关键点绘制 (红点)
                            drawLandmarks(canvasCtx, landmarks, {color: '#FF0000', lineWidth: 1, radius: 3});
                            
                            // 比耶 (Victory) 跳转逻辑
                            const isV = landmarks[8].y < landmarks[6].y && landmarks[12].y < landmarks[10].y && landmarks[16].y > landmarks[14].y;
                            if (isV) {
                                ui.innerText = "✌️ Gesture Detected!";
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }
                        }
                    } else {
                        ui.innerText = "Searching for Hand...";
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
        """, height=450)

        # 隐藏的触发按钮
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
            p = f"用户在{st.session_state.env_data['city']}({st.session_state.env_data['temp']}°C)面前。根据面部表情给出10字建议。JSON:{{'label':'状态','text':'建议'}}"
            try:
                r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], response_format={'type':'json_object'})
                res = json.loads(r.choices[0].message.content)
                st.session_state.ai_result = res
                st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **res})
                st.session_state.current_page = "stats"
                st.rerun()
            except: pass

    with col_i:
        st.subheader("📊 表情画像")
        st.markdown(f"""
            <div style="background:white; padding:20px; border-radius:15px; border-left:10px solid #5C6BC0; box-shadow:0 10px 30px rgba(0,0,0,0.1);">
                <small style="color:#999;">AI 实时诊断</small>
                <h2 style="color:#1A237E; margin:10px 0;">{st.session_state.ai_result['label']}</h2>
                <hr>
                <p style="color:#333;">{st.session_state.ai_result['text']}</p>
            </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "stats":
    st.title("📊 历史分析记录")
    if st.button("⬅️ 返回监测站"):
        st.session_state.current_page = "main"
        st.rerun()
    st.table(pd.DataFrame(st.session_state.chat_log))
