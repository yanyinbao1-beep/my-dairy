import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化与设置 ---
st.set_page_config(page_title="Emo-Bot 深度监测", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"happiness": 0.5, "stress": 0.2, "label": "系统待命"}

st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 增强版通知与样式引擎 ---
m = st.session_state.last_metrics
# 动态计算 HSL 颜色：开心(120绿色/45金黄)，悲伤(210蓝色)，焦虑(280紫色)
h_color = 200 - (m['happiness'] * 100) + (m['stress'] * 60)
bg_style = f"hsl({h_color}, 25%, 94%)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_style}; transition: 3s; }}
    .video-container {{
        width: 100%;
        aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0;
        border-radius: 20px;
        overflow: hidden;
        background: #000;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .bot-bubble {{ background: white; border-radius: 15px; padding: 18px; border-left: 6px solid #5C6BC0; margin-bottom: 12px; }}
    </style>
    
    <script>
    // 强制通知激活函数
    window.parent.activateNotify = function() {{
        if (!("Notification" in window)) {{
            alert("此浏览器不支持桌面通知");
            return;
        }}
        Notification.requestPermission().then(permission => {{
            if (permission === "granted") {{
                new Notification("通知已激活 ✅", {{ body: "现在我可以随时通过系统弹窗找你聊天了", icon: "https://cdn-icons-png.flaticon.com/512/204/204345.png" }});
            }} else {{
                alert("通知被屏蔽。请点击地址栏左侧的'锁头'图标手动开启。目前状态: " + permission);
            }}
        }});
    }};

    window.parent.sendPush = function(title, body) {{
        if (Notification.permission === 'granted') {{
            new Notification(title, {{ body: body, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png' }});
        }}
    }};
    </script>
""", unsafe_allow_html=True)

# --- 3. 页面逻辑路由 ---

if st.session_state.current_page == "main":
    st.title("🤖 机器人深度监测站")
    
    # 顶部控制栏
    c_btn1, c_btn2 = st.columns([1, 1])
    with c_btn1:
        if st.button("🔔 1. 激活 Mac 弹窗权限", use_container_width=True):
            components.html("<script>window.parent.activateNotify();</script>", height=0)

    # 1分钟主动决策
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        prompt = f"特征:{st.session_state.face_log[-6:]}。请识别开心、悲伤、焦虑或疲惫。JSON:{{'text':'暖心话','label':'情绪词','happiness':float,'stress':float}}"
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": "你是一个能够精准察觉人类微小情绪起伏的心理观察机器人。"}, {"role": "user", "content": prompt}],
                response_format={'type': 'json_object'}
            )
            data = json.loads(resp.choices[0].message.content)
            record = {"time": datetime.now().strftime("%H:%M"), "message": data['text'], "label": data['label'], "happiness": data['happiness'], "stress": data['stress']}
            st.session_state.chat_log.insert(0, record)
            st.session_state.last_metrics = record
            
            # 触发弹窗
            push_script = f"<script>window.parent.sendPush('观察者：{data['label']}', '{data['text']}');</script>"
            components.html(push_script, height=0)
        except: pass

    # 左右布局
    col_l, col_r = st
