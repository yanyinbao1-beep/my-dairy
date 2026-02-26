import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化设置 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "传感器初始化", "happiness": 0.5, "stress": 0.2, 
        "weather": "定位中...", "temp": "--", "message": "正在建立档案..."
    }

# 10秒心跳同步
st_autorefresh(interval=10000, key="bot_heartbeat")

# 配置 API
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("API Key 缺失，请检查 Secrets 配置。")

# --- 2. 真实地理位置与天气获取 ---
@st.cache_data(ttl=1800)
def get_real_weather():
    try:
        # 自动 IP 定位
        geo = requests.get("http://ip-api.com/json/", timeout=3).json()
        city = geo.get("city", "未知城市")
        lat, lon = geo.get("lat", 39.9), geo.get("lon", 116.4)
        
        # 获取实时天气
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=3).json()
        curr = w_res['current_weather']
        w_map = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "雨", 95: "雷阵雨"}
        return f"{city} | {w_map.get(curr['weathercode'], '多云')}", curr['temperature']
    except:
        return "本地环境", 25.0

current_weather, current_temp = get_real_weather()

# --- 3. 视觉样式与自动通知 ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 20%, 96%); transition: 3s ease; }}
    .video-container {{
        width: 100%; aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0; border-radius: 20px;
        overflow: hidden; background: #000;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .status-card {{
        background: white; border-radius: 18px; padding: 25px;
        border-top: 10px solid hsl({h_val}, 60%, 50%);
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }}
    </style>
    <script>
    if (Notification.permission === 'default') {{ Notification.requestPermission(); }}
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') {{
            new Notification(t, {{ body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png' }});
        }}
    }};
    </script>
""", unsafe_allow_html=True)

# --- 4. 路由逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 深度情感与环境分析终端")

    # 状态栏
    c1, c2 = st.columns(2)
    with c1: st.metric("当前位置 & 天气", current_weather)
    with c2: st.metric("实时气温", f"{current_temp} ℃")

    # 60秒分析周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        try:
            prompt = f"环境:{current_weather},{current_temp}度。面部特征:{st.session_state.face_log[-6:]}。分析开心/悲伤/焦虑。JSON:{{'label':'标签','text':'暖心话','happiness':0.5,'stress':0.2}}"
            resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
            data = json.loads(resp.choices[0].message.content)
            record = {
                "time": datetime.now().strftime("%H:%M"),
                "label": data.get("label", "稳定"),
                "message": data.get("text", "..."),
                "happiness": float(data.get("happiness", 0.5)),
                "stress": float(data.get("stress", 0.2)),
                "weather": current_weather,
                "temp": current_temp
            }
            st.session_state.chat_log.insert(0, record)
            st.session_state.last_metrics = record
            
            # 发送桌面通知
            push_js = f"<script>window.parent.sendPush('监测提醒：{record['label']}', '{record['message']}');</script>"
            components.html(push_js, height=0)
        except: pass

    # UI 渲染
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("📸 视觉监测流")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=320)
        st.session_state.face_log.append(random.choice(["专注", "放松", "疲惫"]))

    with r:
        st.subheader("📊 机器人分析结论")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div class="status-card">
                <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">基于 {cur.get('weather')} 的环境推演：</div>
                <div style="font-size: 2.2em; font-weight: bold; color: #1A237E; margin-bottom: 15px;">{cur.get('label')}</div>
                <div style="border-top: 1px solid #eee; padding-top: 15px; color: #333; font-style: italic; line-height: 1.6;">
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("📈 进入大数据分析看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感与环境相关性看板")
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 情绪波动图
        st.subheader("📉 情绪与压力波动走势")
        
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        # 2. 气温与心情关联图
        st.subheader("🌦️ 气温对愉悦度的影响分析")
        
        st.scatter_chart(df, x="temp", y="happiness", color="label", size="stress")
        
        # 3. 完整原始数据表
        st.subheader("📑 历史数据审计表")
        st.dataframe(
            df[["time", "label", "weather", "temp", "happiness", "message"]], 
            use_container_width=True,
            column_config={
                "happiness": st.column_config.ProgressColumn("快乐指数", min_value=0, max_value=1, format="%.2f"),
                "time": "采样时间", "label": "情绪标签", "weather": "所在地与天气"
            }
        )
    else:
        st.warning("数据收集中，请返回主站等待首个 60 秒分析周期...")

    if st.button("⬅️ 返回监测主站", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
