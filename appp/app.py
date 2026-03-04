import streamlit as st
import streamlit.components.v1 as components
try:
    from streamlit_javascript import st_javascript
except ImportError:
    st.error("请确保 requirements.txt 中包含 streamlit-javascript")
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
if "start_time" not in st.session_state: st.session_state.start_time = None
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "神经网络同步中", "happiness": 0.5, "message": "正在连接 DeepSeek 情感大脑..."}

# --- 2. 仪式感动态封面 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .welcome-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 120px; height: 120px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; box-shadow: 0 0 20px #5C6BC0; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .t { margin-top: 30px; color: #5C6BC0; letter-spacing: 5px; font-family: 'Courier New', monospace; font-size: 1.2rem; }
        </style>
        <div class="welcome-box"><div class="ring"></div><div class="t">EMO-BOT INITIALIZING</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.5)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能引擎 ---
st_autorefresh(interval=20000, key="heartbeat") # 每20秒检查一次
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=1800)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return geo.get("city", "未知地区"), w['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# --- 4. 情绪分析逻辑 (解决文字死板) ---
def analyze_now():
    try:
        # 强力 Prompt 引导 AI 产生真实情感，拒绝占位符
        prompt = f"""
        你是一个拥有诗人灵魂的心理分析AI。当前城市：{current_city}，实时气温：{current_temp}℃。
        请观察用户（此时他正专注地看着屏幕），结合环境给出一段深度的、有文学美感的分析。
        严禁返回“标签”或“暖心话”等占位词。
        返回格式必须是 JSON：
        {{
            "label": "四个字的意境词（如：晨露未唏、幽谷听泉）",
            "text": "一段50-80字的感性描述，必须包含对{current_city}当前温度的感官描述，并给出一个治愈建议。",
            "happiness": 0.1-0.9 的随机数值
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
        st.session_state.last_metrics["message"] = f"分析引擎同步中...请检查 Secrets 配置"

# 首屏执行
if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
    analyze_now()

# UI 氛围渲染
h_val = 210 - (float(st.session_state.last_metrics.get('happiness', 0.5)) * 100)
st.markdown(f"<style>.stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s; }}</style>", unsafe_allow_html=True)

# --- 5. 页面布局 ---
if st.session_state.current_page == "main":
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🤖 Emo-Bot 深度监测主控台")
    with c2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([4.5, 5.5])
    
    with col_v:
        st.subheader("📸 视觉监测 (比 ✌️ 跳转)")
        
        # 手势识别与模拟点击跳转
        components.html("""
            <div style="position:relative; width:100%; border-radius:15px; overflow:hidden; background:#000; aspect-ratio:4/3;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <div id="status" style="position:absolute; top:10px; left:10px; color:#00FF00; background:rgba(0,0,0,0.5); padding:4px 10px; border-radius:5px; font-size:12px;">视觉引擎：运行中</div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const status = document.getElementById('status');
                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.75});
                
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        const isVictory = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                        if (isVictory) {
                            status.innerText = "✌️ 识别成功！正在跳转...";
                            // 模拟点击 Streamlit 的 Primary 按钮实现跳转
                            window.parent.document.querySelector('button[kind="primary"]').click();
                        }
                    }
                });

                const camera = new Camera(video, {
                    onFrame: async () => { await hands.send({image: video}); },
                    width: 480, height: 360
                });
                camera.start();
            </script>
        """, height=380)
        
        # 这个按钮会被 JS 自动点击，完成“比耶跳转”
        if st.button("📈 进入分析看板", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 实时推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:20px; padding:25px; border-left:10px solid #5C6BC0; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
                <small style='color:#888'>AI 感知结果：</small>
                <h2 style='color:#1A237E; margin:10px 0;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:15px; font-style:italic; color:#444; line-height:1.7;'>
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.write("---")
        st.caption("提示：每 60 秒自动进行一次深度扫描。")

elif st.session_state.current_page == "stats":
    st.title("📊 情感数据洞察中心")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.line_chart(df.set_index("time")["happiness"])
        
        st.write("### 📑 历史详细日志")
        st.dataframe(df[["time", "label", "weather", "temp", "happiness", "message"]], use_container_width=True)
    else:
        st.warning("暂无数据。")
    
    if st.button("⬅️ 返回监测终端", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
