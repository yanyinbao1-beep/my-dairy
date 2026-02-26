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
st.set_page_config(page_title="EMO-Robot 深度监测", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"happiness": 0.5, "stress": 0.2, "label": "待命"}

st_autorefresh(interval=10000, key="bot_heartbeat")
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 2. 强化版通知引擎 (支持 Mac 浏览器沙盒穿透) ---
st.markdown("""
    <script>
    // 定义全局通知函数
    window.parent.sendPush = function(title, body) {
        if (Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'
            });
        } else {
            console.log("通知权限未开启");
        }
    };
    
    // 初始化权限请求
    window.parent.initNotify = function() {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification("通知系统已激活", {body: "机器人现在可以在后台陪伴你了"});
            }
        });
    };
    </script>
""", unsafe_allow_html=True)

# --- 3. 动态 UI 样式 ---
m = st.session_state.last_metrics
h = 220 - (m['happiness'] * 100)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h}, 30%, 95%); transition: 3s; }}
    .video-container {{ width: 100%; aspect-ratio: 4/3; border: 4px solid #5C6BC0; border-radius: 20px; overflow: hidden; background: #000; }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .bot-bubble {{ background: white; border-radius: 15px; padding: 15px; border-left: 6px solid #5C6BC0; margin-bottom: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 主页面逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 机器人监测站")
    
    # 【新增：Mac 专用激活按钮】
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🔔 步骤 1：激活系统通知权限"):
            components.html("<script>window.parent.initNotify();</script>", height=0)
            st.toast("请在弹出的系统窗口中点击'允许'")

    # 60秒总结逻辑
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        prompt = f"分析特征:{st.session_state.face_log[-5:]}。JSON:{{'text':'暖心话','label':'情绪词','happiness':0.5,'stress':0.2}}"
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={'type': 'json_object'}
            )
            data = json.loads(resp.choices[0].message.content)
            record = {"time": datetime.now().strftime("%H:%M"), "message": data['text'], "label": data['label'], "happiness": data['happiness'], "stress": data['stress']}
            st.session_state.chat_log.insert(0, record)
            st.session_state.last_metrics = record
            
            # --- 核心：发送通知 ---
            push_script = f"<script>window.parent.sendPush('机器人观察：{record['label']}', '{record['message']}');</script>"
            components.html(push_script, height=0)
        except: pass

    # 画面展示
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("📷 观察窗口")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=320)
        f = random.choice(["开心", "沉思", "疲惫"])
        st.session_state.face_log.append(f)
        st.metric("情绪状态", st.session_state.last_metrics['label'])

    with c2:
        st.subheader("💬 对话记录")
        for chat in st.session_state.chat_log[:3]:
            st.markdown(f"<div class='bot-bubble'><b>{chat['label']}</b><br>{chat['message']}</div>", unsafe_allow_html=True)
        
        if st.button("📊 大数据看板"):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log)
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
    if st.button("返回"):
        st.session_state.current_page = "main"
        st.rerun()
