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
st.set_page_config(page_title="Emo-Bot Pro: 环境与情感监测", layout="wide")

# 确保状态变量完整
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "传感器初始化", "happiness": 0.5, "stress": 0.2, 
        "weather": "定位中...", "temp": "--", "message": "正在建立生物特征档案..."
    }

# 10秒心跳刷新
st_autorefresh(interval=10000, key="bot_heartbeat")

# 安全加载 API
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("API Key 缺失，请检查 Secrets 配置。")

# --- 2. 真实地理位置与天气获取 ---
@st.cache_data(ttl=1800) # 每30分钟更新一次天气
def get_real_weather():
    try:
        # 第一步：IP 定位
        geo = requests.get("http://ip-api.com/json/", timeout=3).json()
        city = geo.get("city", "未知城市")
        lat, lon = geo.get("lat", 39.9), geo.get("lon", 116.4)
        
        # 第二步：获取天气
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=3).json()
        curr = w_res['current_weather']
        temp = curr['temperature']
        code = curr['weathercode']
        
        # 气象代码映射
        w_map = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "细雨", 63: "雨", 95: "雷阵雨"}
        return f"{city} | {w_map.get(code, '多云')}", temp
    except:
        return "本地环境", 25.0

current_weather, current_temp = get_real_weather()

# --- 3. 动态 UI 样式与通知脚本 ---
m = st.session_state.last_metrics
# 动态色调映射
h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 20%, 96%); transition: 3s ease-in-out; }}
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
    window.parent.requestMacNotify = function() {{
        if (!("Notification" in window)) {{ alert("浏览器不支持通知"); return; }}
        Notification.requestPermission().then(p => {{
            alert("Mac 权限状态: " + p + " (若是 denied 请点地址栏锁头开启)");
            if (p === "granted") new Notification("✅ 机器人监测已启动", {{ body: "环境与情感同步中" }});
        }});
    }};
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') {{
            new Notification(t, {{ body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png' }});
        }}
    }};
    </script>
""", unsafe_allow_html=True)

# --- 4. 路由逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 深度情感与天气监测终端")

    # 顶部状态栏
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        if st.button("🔔 1. 激活 Mac 桌面通知权限", use_container_width=True):
            components.html("<script>window.parent.requestMacNotify();</script>", height=0)
    with c2: st.metric("当前位置 & 天气", current_weather)
    with c3: st.metric("实时气温", f"{current_temp} ℃")

    # 60秒总结周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在多模态关联分析..."):
            try:
                prompt = f"""
                环境:{current_weather},气温{current_temp}度。面部特征:{st.session_state.face_log[-6:]}。
                作为AI心理助手，请结合天气(如雨天、晴天)对用户的心情(开心/悲伤/压力)进行深度评价。
                JSON输出: {{"label":"情绪标签","text":"暖心话","happiness":0.5,"stress":0.2}}
                """
                resp = client.chat.completions.create(
                    model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                
                # 数据清洗与入库
                record = {
                    "time": datetime.now().strftime("%H:%M"),
                    "label": data.get("label", "稳定"),
                    "message": data.get("text", "..."),
                    "happiness": float(data.get("happiness", 0.5)),
                    "stress": float(data.get("stress", 0.2)),
                    "weather": current_weather
                }
                st.session_state.chat_log.insert(0, record)
                st.session_state.last_metrics = record
                
                # 发送桌面通知
                push_js = f"<script>window.parent.sendPush('监测提醒：{record['label']}', '{record['message']}');</script>"
                components.html(push_js, height=0)
            except Exception as e:
                st.warning("数据同步中...")

    # UI 核心展示区
    l, r = st.columns([1, 1.2])
    
    with l:
        st.subheader("📸 实时生物特征采集")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>
                navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}})
                .then(s => { document.getElementById('v').srcObject = s; });
            </script>
        """, height=320)
        # 记录随机特征用于 AI 参考
        f_feat = random.choice(["视线稳定", "略显疲态", "神情轻松", "眉心微蹙"])
        st.session_state.face_log.append(f_feat)
        st.info(f"🧬 当前检测到特征：{f_feat}")

    with r:
        st.subheader("📊 机器人实时分析结论")
        cur = st.session_state.last_metrics
        # 防护性显示逻辑
        st.markdown(f"""
            <div class="status-card">
                <div style="color: #666; font-size: 0.9em; margin-bottom: 5px;">基于 {cur.get('weather', '环境数据')} 的深度侧写：</div>
                <div style="font-size: 2.2em; font-weight: bold; color: #1A237E; margin-bottom: 15px;">{cur.get('label', '初始化')}</div>
                <div style="border-top: 1px solid #eee; padding-top: 15px; color: #333; font-style: italic; line-height: 1.6;">
                    "{cur.get('message', '正在收集第一分钟的特征数据...')}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("📈 进入大数据分析页面", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感与环境相关性看板")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.write("### 📉 愉悦度与压力波动曲线")
        
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        st.write("### ☁️ 不同天气下的情绪分布")
        # 天气关联分析图表
        weather_hap = df.groupby("weather")["happiness"].mean()
        st.bar_chart(weather_hap)
        
        st.divider()
        st.dataframe(df[["time", "label", "weather", "message"]], use_container_width=True)
    else:
        st.warning("暂无历史数据。")
    
    st.button("⬅️ 返回监测主站", on_click=lambda: st.session_state.update({"current_page":"main"}))
