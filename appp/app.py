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
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = None
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "初始化", "happiness": 0.5, "weather": "获取中...", "message": "系统准备中..."}

# --- 2. 动态欢迎封面 (保持不变) ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .welcome-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 120px; height: 120px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite, glow 2s ease-in-out infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 10px #5C6BC0; } 50% { box-shadow: 0 0 30px #5C6BC0; } }
        .t { margin-top: 30px; color: #5C6BC0; letter-spacing: 5px; font-family: monospace; }
        </style>
        <div class="welcome-box"><div class="ring"></div><div class="t">EMO-BOT INITIALIZING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.5)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能引擎 ---
st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=1800)
def get_env_data():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo.get("city", "未知地区")
        w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return city, w_res['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env_data()

# --- 4. 界面渲染 ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
st.markdown(f"<style>.stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s; }}</style>", unsafe_allow_html=True)

if st.session_state.current_page == "main":
    # 顶部信息栏
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🤖 深度情绪监测终端 (手势交互版)")
    with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    # [核心修改：情绪生成逻辑]
    if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
        try:
            prompt = f"环境:{current_city},{current_temp}度。JSON:{{'label':'标签','text':'暖心话','happiness':0.5}}"
            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
            data = json.loads(resp.choices[0].message.content)
            record = {"time": datetime.now().strftime("%H:%M"), "label": data['label'], "message": data['text'], "happiness": data['happiness'], "weather": current_city, "temp": current_temp}
            st.session_state.chat_log.insert(0, record); st.session_state.last_metrics = record
            st.session_state.start_time = datetime.now()
        except Exception as e:
            st.error(f"AI 连接中断，请检查 API Key。错误信息: {e}")

    # [4:6 比例布局]
    col_v, col_i = st.columns([4, 6])
    
    with col_v:
        st.subheader("📸 视觉监测 (比 ✌️ 跳转)")
        
        components.html("""
            <div style="position:relative; width:100%; border-radius:20px; overflow:hidden; background:#000; aspect-ratio:4/3;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <div id="stat" style="position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.6); color:#00FF00; padding:5px 10px; border-radius:8px; font-family:sans-serif; font-size:12px;">模型加载中...</div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const stat = document.getElementById('stat');
                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                
                hands.setOptions({ maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
                
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        // 优化后的 ✌️ 判定：食指(8)和中指(12)显著高于无名指(16)和手掌(0)
                        const isVictory = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                        if (isVictory) {
                            stat.innerText = "✌️ 识别成功！正在跳转...";
                            stat.style.color = "#FFD700";
                            window.parent.postMessage({type: 'GOTO_STATS'}, '*');
                        } else {
                            stat.innerText = "已就绪：请对着镜头比 ✌️";
                            stat.style.color = "#00FF00";
                        }
                    } else { stat.innerText = "未检测到手部"; }
                });

                const camera = new Camera(video, { onFrame: async () => { await hands.send({image: video}); }, width: 480, height: 360 });
                camera.start();
            </script>
        """, height=380)
        
        # 手动保底按钮
        if st.button("📈 手动进入分析看板", use_container_width=True):
            st.session_state.current_page = "stats"; st.rerun()

    with col_i:
        st.subheader("📊 实时推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:20px; padding:25px; border-left:10px solid #5C6BC0; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
                <small style='color:#888'>AI 解析结果：</small>
                <h2 style='color:#1A237E; margin:10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic; line-height:1.6;'>"{cur.get('message')}"</div>
            </div>
        """, unsafe_allow_html=True)
        st.caption("提示：每 60 秒系统会自动重新扫描一次环境与情绪。")

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据看板")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.write("### 📉 愉悦度波动趋势")
        st.line_chart(df.set_index("time")["happiness"])
        
        st.write("### 📑 历史详细记录")
        st.dataframe(df[["time", "label", "weather", "temp", "happiness", "message"]], use_container_width=True,
                     column_config={"happiness": st.column_config.ProgressColumn("得分", min_value=0, max_value=1)})
    else:
        st.warning("暂无数据，请返回主页等待扫描。")
    
    if st.button("⬅️ 返回监测终端", use_container_width=True):
        st.session_state.current_page = "main"; st.rerun()
