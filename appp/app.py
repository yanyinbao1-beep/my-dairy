import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro: 全功能版", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "传感器初始化", "happiness": 0.5, "stress": 0.2, 
        "weather": "自动定位中...", "temp": "--", "message": "正在建立档案..."
    }

st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 地理位置与天气 ---
@st.cache_data(ttl=1800)
def get_real_weather():
    try:
        geo = requests.get("http://ip-api.com/json/", timeout=3).json()
        city = geo.get("city", "本地")
        lat, lon = geo.get("lat", 39.9), geo.get("lon", 116.4)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=3).json()
        curr = w_res['current_weather']
        w_map = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "雨", 95: "雷阵雨"}
        return f"{city} | {w_map.get(curr['weathercode'], '多云')}", curr['temperature']
    except:
        return "本地环境", 25.0

current_weather, current_temp = get_real_weather()

# --- 3. UI 样式 ---
m = st.session_state.last_metrics
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)

st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 20%, 96%); transition: 3s; }}
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
    st.title("🤖 机器人多模态分析中心")

    c1, c2 = st.columns(2)
    with c1: st.metric("当前位置 & 天气", current_weather)
    with c2: st.metric("实时气温", f"{current_temp} ℃")

    # 60秒总结周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        try:
            prompt = f"环境:{current_weather},{current_temp}度。特征:{st.session_state.face_log[-6:]}。JSON:{{'label':'标签','text':'暖心话','happiness':0.5,'stress':0.2}}"
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
            
            # 自动通知
            push_js = f"<script>window.parent.sendPush('监测提醒：{record['label']}', '{record['message']}');</script>"
            components.html(push_js, height=0)
        except: pass

    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("📸 视觉流监测")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=320)
        st.session_state.face_log.append(random.choice(["专注", "放松", "疲惫"]))

    with r:
        st.subheader("📊 实时结论")
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div class="status-card">
                <div style="color: #666; font-size: 0.9em;">基于 {cur.get('weather')} 的分析</div>
                <div style="font-size: 2em; font-weight: bold; color: #1A237E; margin: 10px 0;">{cur.get('label')}</div>
                <div style="border-top: 1px solid #eee; padding-top: 10px; color: #333; font-style: italic;">
                    "{cur.get('message')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("📈 进入大数据分析看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据相关性分析")
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 情绪波动图
        st.subheader("📉 情绪与压力波动走势")
        
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        # 2. 天气关联分析
        st.subheader("🌡️ 气温与心情的相关性")
        
        st.scatter_chart(df, x="temp", y="happiness", color="label", size="stress")
        
        # 3. 完整原始数据表
        st.subheader("📑 历史数据审计表")
        st.dataframe(
            df[["time", "label", "weather", "temp", "happiness", "stress", "message"]], 
            use_container_width=True,
            column_config={
                "happiness": st.column_config.ProgressColumn("快乐指数", min_value=0, max_value=1),
                "stress": st.column_config.ProgressColumn("压力指数", min_value=0, max_value=1)
            }
        )
        
        # 导出功能
        st.download_button("📥 导出分析数据 (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "emo_report.csv")
    else:
        st.warning("暂无充足数据，请返回主站等待首个 60 秒分析周期完成。")

    if st.button("⬅️ 返回监测终端", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
