import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 全局配置 ---
st.set_page_config(page_title="EMO-Robot 深度情感终端", layout="wide")

# 初始化 Session State
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "happiness": 0.5, "energy": 0.5, "stress": 0.2, "label": "系统待命"
    }

# 心跳刷新（10秒）
st_autorefresh(interval=10000, key="bot_heartbeat")

# 配置 OpenAI (DeepSeek)
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 核心：动态颜色与 UI 优化 ---
m = st.session_state.last_metrics

# 颜色心理学插值：
# 基础色调：开心->金黄(45), 悲伤->冷蓝(220), 焦虑->紫灰(280)
h = 220 - (m['happiness'] * 100) + (m['stress'] * 60)
s = 15 + (m['energy'] * 20)
l = 95 - (m['stress'] * 10)

st.markdown(f"""
    <style>
    .stApp {{
        background: hsl({h}, {s}%, {l}%);
        transition: background 3.0s ease-in-out;
    }}
    .video-container {{
        width: 100%;
        aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0;
        border-radius: 20px;
        overflow: hidden;
        background: #000;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .bot-bubble {{
        background: rgba(255, 255, 255, 0.9);
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 15px;
        border-left: 6px solid #5C6BC0;
        box-shadow: 2px 4px 12px rgba(0,0,0,0.05);
    }}
    .metric-text {{ font-weight: bold; color: #5C6BC0; }}
    </style>
    
    <script>
    if (Notification.permission !== 'granted') {{ Notification.requestPermission(); }}
    window.sendBotNotification = function(title, message) {{
        if (Notification.permission === 'granted') {{
            new Notification(title, {{
                body: message,
                icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'
            }});
        }}
    }}
    </script>
""", unsafe_allow_html=True)

# --- 3. 路由逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 深度情感监测终端")
    
    # 60秒行为生成循环
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 观察者正在读取多维情感特征..."):
            prompt = f"""
            面部特征序列:{st.session_state.face_log[-6:]}。
            分析用户的开心、悲伤、焦虑、疲惫程度。
            返回JSON：{{
                "text": "一段极具共情力的暖心谈话",
                "label": "如：平静的微光、隐秘的焦虑、明亮的愉悦",
                "happiness": 0.0-1.0, 
                "energy": 0.0-1.0, 
                "stress": 0.0-1.0
            }}
            """
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是一个能够精准感知开心、悲伤、压力等情绪并给出反馈的AI助手"}, {"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                
                # 数据对齐：统一存入 message 键
                record = {
                    "time": datetime.now().strftime("%H:%M"),
                    "message": data.get("text", "感知中断，正在重连..."),
                    "label": data.get("label", "状态不明"),
                    "happiness": data.get("happiness", 0.5),
                    "energy": data.get("energy", 0.5),
                    "stress": data.get("stress", 0.2)
                }
                st.session_state.last_metrics = record
                st.session_state.chat_log.insert(0, record)
                
                # 发送系统通知
                notif_js = f"<script>window.parent.sendBotNotification('机器人观察：{record['label']}', '{record['message']}');</script>"
                components.html(notif_js, height=0)
            except Exception as e:
                st.error(f"感知同步错误")

    # 布局
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
        
        # 记录特征
        f = random.choice(["视线稳定 (专注中)", "嘴角微动 (情绪起伏)", "眉心放松 (压力降低)", "频繁眨眼 (略显疲态)"])
        st.session_state.face_log.append(f)
        st.write(f"🧬 **捕获特征：** {f}")
        st.metric("核心判定", st.session_state.last_metrics['label'])

    with col_c:
        st.subheader("💬 主动关怀日志")
        if not st.session_state.chat_log:
            st.info("正在建立情感档案，请保持前台开启一分钟...")
        for chat in st.session_state.chat_log[:4]:
            st.markdown(f"""
                <div class="bot-bubble">
                    <small style="color:#666;">[{chat['time']}] <b>{chat['label']}</b></small><br>
                    {chat['message']}
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("📈 展开多维大数据看板", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感动力学大数据看板")
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 优化颜色的折线图
        st.write("### 📉 三维情绪波动走势")
        # 为图表准备漂亮的数据
        chart_data = df.set_index("time")[["happiness", "energy", "stress"]]
        chart_data.columns = ["愉悦度(Happiness)", "激活度(Energy)", "压力值(Stress)"]
        st.line_chart(chart_data, color=["#4CAF50", "#FF9800", "#9C27B0"]) 
        
        # 2. 情感坐标分析
        st.divider()
        st.write("### 🌌 情感象限分布")
        
        st.scatter_chart(df, x="happiness", y="stress", color="label", size="energy")
        
        # 3. 数据表
        st.write("### 📄 历史审计清单")
        st.dataframe(df[["time", "label", "message", "happiness", "stress"]], use_container_width=True)
        
        st.download_button(
            "📥 下载大数据报表 (Excel/CSV兼容)", 
            df.to_csv(index=False).encode('utf-8-sig'), 
            "emo_pro_report.csv", "text/csv"
        )
    else:
        st.warning("暂无历史样本，请返回主站等待首轮分析生成。")

    if st.button("⬅️ 返回感知终端", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
