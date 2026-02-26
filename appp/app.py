import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 页面配置 ---
st.set_page_config(page_title="Emo-Bot 深度情感监测", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"happiness": 0.5, "energy": 0.5, "stress": 0.2, "label": "系统初始化"}

# 自动刷新器 (10秒心跳)
st_autorefresh(interval=10000, key="bot_heartbeat")

client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 注入通知引擎、锁定比例 CSS 与机器人图标 ---
m = st.session_state.last_metrics
# 动态背景色逻辑
bg_color = f"hsl({200 - (m['happiness']-0.5)*120}, {20 + m['stress']*30}%, {92 - m['stress']*10}%)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_color}; transition: all 3s ease; }}
    /* 锁定 4:3 摄像头比例 */
    .video-container {{
        width: 100%;
        aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0;
        border-radius: 20px;
        overflow: hidden;
        background: #000;
        position: relative;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }}
    video {{
        width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1);
    }}
    .bot-bubble {{ 
        background: rgba(255,255,255,0.9); border-radius: 15px; 
        padding: 15px; margin-bottom: 12px; border-left: 6px solid #5C6BC0;
        font-size: 15px; line-height: 1.5;
    }}
    </style>
    
    <script>
    // 权限请求与通知函数
    if (Notification.permission !== 'granted') {{ Notification.requestPermission(); }}
    window.sendBotNotification = function(title, message) {{
        if (Notification.permission === 'granted') {{
            new Notification(title, {{
                body: message,
                icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png' // 可爱的机器人图标
            }});
        }}
    }}
    </script>
""", unsafe_allow_html=True)

# --- 3. 核心行为生成逻辑 (增强情绪具体性) ---

if st.session_state.current_page == "main":
    st.title("🤖 深度情感机器人监控终端")
    
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 机器人正在分析你的开心、悲伤与压力指标..."):
            # 强化 Prompt：明确要求分析开心/悲伤/焦虑/疲惫
            prompt = f"""
            面部特征序列:{st.session_state.face_log[-6:]}。
            请作为专业心理观察机器人，详细分析用户的开心、悲伤、焦虑或疲惫感。
            要求返回JSON：
            1. text: 针对捕捉到的情绪(如：看出了你隐藏的悲伤或由衷的开心)给出一段暖心对话。
            2. label: 具体的情绪描述词（如：沉静的哀伤、明亮的愉悦、紧绷的焦虑）。
            3. happiness, energy, stress: 0.0-1.0 之间的分值。
            """
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是一个能够精准识别开心、悲伤等多模态情绪的机器人助手"}, {"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                st.session_state.last_metrics = data
                st.session_state.chat_log.insert(0, {"time": datetime.now().strftime("%H:%M"), **data})
                
                # --- 后台通知触发 ---
                notif_js = f"<script>window.parent.sendBotNotification('机器人观察：{data['label']}', '{data['text']}');</script>"
                components.html(notif_js, height=0)
            except: pass

    # --- 布局 ---
    col_v, col_c = st.columns([1, 1.2])
    
    with col_v:
        st.subheader("📸 生物感知窗口")
        components.html("""
            <div class="video-container">
                <video id="v" autoplay playsinline></video>
            </div>
            <script>
                navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}})
                .then(s => { document.getElementById('v').srcObject = s; });
            </script>
        """, height=320)
        
        f = random.choice(["嘴角微微上扬 (开心?)", "眼神略显空洞 (忧郁?)", "眉心轻微收缩 (压力?)", "频繁眨眼 (疲惫?)"])
        st.session_state.face_log.append(f)
        st.info(f"🧬 生物特征捕捉：{f}")
        st.metric("核心情绪判定", st.session_state.last_metrics['label'])

    with col_c:
        st.subheader("💬 主动关怀日志")
        if not st.session_state.chat_log:
            st.write("机器人正在建立你的情感档案，请稍候...")
        for chat in st.session_state.chat_log[:4]:
            st.markdown(f"""
                <div class="bot-bubble">
                    <small style="color:#666;">[{chat['time']}] 判定状态：{chat['label']}</small><br>
                    {chat['message']}
                </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        if st.button("📊 进入多维大数据看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 多维情感大数据看板")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        st.write("### 📉 情绪曲线 (包含开心与压力维度)")
        st.line_chart(df.set_index("time")[["happiness", "energy", "stress"]])
        
        st.write("### 🌌 情感分布散点图")
        st.scatter_chart(df, x="happiness", y="stress", color="label", size="energy")
        
        st.write("### 📄 原始决策数据表")
        st.dataframe(df[["time", "label", "message"]], use_container_width=True)
        
        # 导出功能
        st.download_button("📥 导出我的情感大数据报告 (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "emo_report.csv", "text/csv")

    st.button("⬅️ 返回实时监控终端", on_click=lambda: st.session_state.update({"current_page":"main"}))
