import streamlit as st
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 初始化状态
if "welcome_finished" not in st.session_state: st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = None
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "正在深度分析...", "happiness": 0.5, "message": "正在连接神经网络，请稍候..."}

# --- 2. 动态加载封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 100px; height: 100px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .text { margin-top: 20px; color: #5C6BC0; letter-spacing: 4px; font-family: monospace; }
        </style>
        <div class="loader-box"><div class="ring"></div><div class="text">EMO-BOT CORE LOADING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.5)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能引擎 ---
st_autorefresh(interval=15000, key="heartbeat") # 增加到15秒，给AI留出生成时间
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=1800)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return geo.get("city", "北京"), w['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# --- 4. 情绪生成函数 (解决文字死板问题) ---
def generate_emotion():
    try:
        # 强化提示词：要求AI必须具体化
        prompt = f"""
        你是一个专业的情绪分析AI。当前环境：{current_city}，温度{current_temp}度。
        请根据用户正对摄像头的状态（专注、平和），生成一段具体的、具有文学色彩的情绪画像。
        严禁使用“标签”、“暖心话”这种占位符。
        必须严格返回JSON格式：
        {{
            "label": "这里写一个四个字的创意词，如'静水流深'、'暖阳煦煦'",
            "text": "这里写一段50字左右的感性建议，要结合当前{current_temp}度的天气",
            "happiness": 0.1到0.9之间的随机数
        }}
        """
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            response_format={'type': 'json_object'}
        )
        data = json.loads(resp.choices[0].message.content)
        record = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "label": data['label'],
            "message": data['text'],
            "happiness": data['happiness'],
            "weather": current_city,
            "temp": current_temp
        }
        st.session_state.chat_log.insert(0, record)
        st.session_state.last_metrics = record
        st.session_state.start_time = datetime.now()
    except Exception as e:
        st.session_state.last_metrics["message"] = f"分析引擎同步中...({str(e)[:20]})"

# 启动或每分钟触发
if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
    generate_emotion()

# --- 5. 页面渲染 ---
h_val = 210 - (float(st.session_state.last_metrics.get('happiness', 0.5)) * 100)
st.markdown(f"<style>.stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s; }}</style>", unsafe_allow_html=True)

if st.session_state.current_page == "main":
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🤖 Emo-Bot 深度监测终端")
    with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([4, 6])
    
    with col_v:
        st.subheader("📸 视觉交互 (比 ✌️ 跳转)")
        
        # 解决跳转问题的关键 JavaScript
        js_code = """
        const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
        hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.7});
        hands.onResults((res) => {
            if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                const lm = res.multiHandLandmarks[0];
                const isVictory = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                if (isVictory) {
                    // 强力触发：改变父级页面的 URL hash 或发送特殊事件
                    window.parent.document.querySelector('button[kind="primary"]').click();
                }
            }
        });
        """
        
        components.html(f"""
            <div style="position:relative; width:100%; border-radius:15px; overflow:hidden; background:#000; aspect-ratio:4/3;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <div id="stat" style="position:absolute; top:10px; left:10px; color:#00FF00; font-family:sans-serif; background:rgba(0,0,0,0.5); padding:4px 8px; border-radius:5px; font-size:12px;">视觉引擎已启动</div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const stat = document.getElementById('stat');
                {js_code}
                const camera = new Camera(video, {{ onFrame: async () => {{ await hands.send({{image: video}}); }}, width: 480, height: 360 }});
                camera.start();
            </script>
        """, height=380)

        # 核心跳转保底：这个 Primary 按钮会被 JS 自动点击
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 实时推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:20px; padding:25px; border-left:10px solid #5C6BC0; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
                <small style='color:#888'>AI 解析画像：</small>
                <h2 style='color:#1A237E; margin:10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic; line-height:1.6; color:#444;'>
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.write("---")
        st.caption("提示：每 60 秒自动更新一次。若手势失效，请确保摄像头画面清晰且背景不杂乱。")

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据中心")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        st.line_chart(df.set_index("time")["happiness"])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("数据收集中...")
    
    if st.button("⬅️ 返回监测主站", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
