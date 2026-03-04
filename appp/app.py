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
if "start_time" not in st.session_state: st.session_state.start_time = None
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"label": "神经网络同步中", "happiness": 0.5, "message": "正在初始化情感监测引擎..."}

# --- 2. 动态加载封面 (保留原要求) ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a1118; }
        .loader-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .ring { width: 100px; height: 100px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0; border-radius: 50%; animation: spin 1s linear infinite; box-shadow: 0 0 20px #5C6BC0; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .text { margin-top: 25px; color: #5C6BC0; letter-spacing: 5px; font-family: 'Courier New', monospace; font-size: 1.1rem; }
        </style>
        <div class="loader-box"><div class="ring"></div><div class="text">EMO-BOT CORE INITIALIZING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.5)
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 环境与 AI 引擎 ---
st_autorefresh(interval=20000, key="heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

@st.cache_data(ttl=1800)
def get_env():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=5).json()
        city = geo.get("city", "未知城市")
        w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true").json()
        return city, w_res['current_weather']['temperature']
    except: return "本地环境", 25.0

current_city, current_temp = get_env()

# --- 4. 深度情绪生成 (解决文字死板) ---
def analyze_emotion():
    try:
        prompt = f"""
        你是一个拥有诗人灵魂的情感分析AI。
        当前环境信息：城市【{current_city}】，气温【{current_temp}℃】。
        任务：生成一段极其感性、像电影独白一样的情绪分析画像。
        禁止准则：严禁使用“标签”、“建议”、“暖心话”这种模板词。
        必须严格返回JSON：
        {{
            "label": "四个字的文学词汇（如：星河静默、春山可望）",
            "text": "一段60字左右的感悟，必须提到在{current_city}这{current_temp}度的天气里，人的心情该如何安放。",
            "happiness": 0.1-0.9的随机浮点数
        }}
        """
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
        data = json.loads(resp.choices[0].message.content)
        record = {"time": datetime.now().strftime("%H:%M:%S"), "label": data['label'], "message": data['text'], "happiness": data['happiness'], "weather": current_city, "temp": current_temp}
        st.session_state.chat_log.insert(0, record)
        st.session_state.last_metrics = record
        st.session_state.start_time = datetime.now()
    except: pass

if st.session_state.start_time is None or (datetime.now() - st.session_state.start_time).seconds >= 60:
    analyze_emotion()

# 背景动态色彩映射
h_val = 210 - (float(st.session_state.last_metrics.get('happiness', 0.5)) * 100)
st.markdown(f"<style>.stApp {{ background: hsl({h_val}, 15%, 96%); transition: 3s; }}</style>", unsafe_allow_html=True)

# --- 5. 页面路由 ---
if st.session_state.current_page == "main":
    t1, t2 = st.columns([3, 1])
    with t1: st.title("🤖 Emo-Bot 深度监测终端")
    with t2: st.info(f"📍 {current_city} | 🌡️ {current_temp}℃")

    col_v, col_i = st.columns([4.5, 5.5])
    
    with col_v:
        st.subheader("📸 视觉监测 (比 ✌️ 跳转分析)")
        
        # 核心手势代码：使用 XPath 强行穿透沙箱点击按钮
        components.html("""
            <div style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:15px; overflow:hidden;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <div id="stat" style="position:absolute; top:10px; left:10px; color:#00FF00; background:rgba(0,0,0,0.6); padding:4px 10px; border-radius:5px; font-size:12px;">视觉流：正常</div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script>
                const video = document.getElementById('v');
                const stat = document.getElementById('stat');
                const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
                
                hands.setOptions({maxNumHands: 1, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5});
                
                hands.onResults((res) => {
                    if (res.multiHandLandmarks && res.multiHandLandmarks.length > 0) {
                        const lm = res.multiHandLandmarks[0];
                        // ✌️ 判定逻辑：食指中指伸直，无名指弯曲
                        const isVictory = lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y;
                        if (isVictory) {
                            stat.innerText = "✌️ 捕捉！正在尝试跳转...";
                            stat.style.color = "#FFD700";
                            // 暴力查找包含“进入分析看板”文字的按钮并模拟点击
                            const btn = window.parent.document.evaluate("//button[contains(., '进入分析看板')]", window.parent.document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (btn) btn.click();
                        }
                    } else { stat.innerText = "已就绪：请比 ✌️"; stat.style.color = "#00FF00"; }
                });
                const camera = new Camera(video, {onFrame: async () => { await hands.send({image: video}); }, width: 480, height: 360});
                camera.start();
            </script>
        """, height=380)
        
        # 这个按钮是 JS 跳转的唯一目标，必须保留
        if st.button("📈 进入分析看板", use_container_width=True, type="primary"):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📊 实时情感推演")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div style="background:white; border-radius:20px; padding:30px; border-left:12px solid #5C6BC0; box-shadow:0 15px 35px rgba(0,0,0,0.08);">
                <small style='color:#999; text-transform:uppercase;'>Sensory Image / 感官画像</small>
                <h2 style='color:#1A237E; margin:15px 0; font-family:serif;'>{cur.get('label')}</h2>
                <div style='border-top:1px solid #eee; padding-top:20px; font-size:1.1rem; line-height:1.8; color:#333; font-style:italic;'>
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.caption("提示：由于 AI 生成需要时间，请比 ✌️ 后稍等 1-2 秒。")

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据相关性分析")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        st.write("### 📈 愉悦度时序波动")
        st.line_chart(df.set_index("time")["happiness"])
        
        st.write("### 📑 历史监测日志（全环境记录）")
        st.dataframe(df[["time", "label", "weather", "temp", "happiness", "message"]], use_container_width=True)
    else:
        st.warning("暂无历史数据。")
    
    if st.button("⬅️ 返回监测主站", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
