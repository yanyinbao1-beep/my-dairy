import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化 (防御性编程) ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "face_log" not in st.session_state: st.session_state.face_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
# 初始指标
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "系统待命", "happiness": 0.5, "stress": 0.2, "message": "正在扫描生物特征..."
    }

st_autorefresh(interval=10000, key="bot_heartbeat")

# 配置 API
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("请在 Secrets 中配置 API Key")

# --- 2. 视觉与通知引擎 ---
m = st.session_state.last_metrics
# 动态色调映射：开心偏明黄色，悲伤偏深蓝色
h_val = 210 - (float(m.get('happiness', 0.5)) * 110)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 30%, 94%); transition: 3s ease; }}
    .video-container {{
        width: 100%; aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0; border-radius: 20px;
        overflow: hidden; background: #000;
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    /* 情绪状态卡片 */
    .status-card {{
        background: white; border-radius: 15px; padding: 20px;
        border-top: 10px solid hsl({h_val}, 70%, 50%);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px;
    }}
    </style>
    <script>
    window.parent.activateNotify = function() {{
        Notification.requestPermission().then(p => {{
            alert("Mac 权限状态: " + p);
            if(p === "granted") new Notification("✅ 守护模式已开启");
        }});
    }};
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') new Notification(t, {{body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'}});
    }};
    </script>
""", unsafe_allow_html=True)

# --- 3. 页面逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 深度情感监测终端")
    
    # 权限激活按钮
    if st.button("🔔 激活 Mac 桌面通知 (初次运行请点此并允许)", use_container_width=True):
        components.html("<script>window.parent.activateNotify();</script>", height=0)

    # 60秒总结逻辑
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在多模态分析你的实时状态..."):
            try:
                # 强化 Prompt，要求明确区分标签和对话内容
                prompt = f"""
                当前特征:{st.session_state.face_log[-6:]}。
                1. 识别核心情绪标签（如：由衷的开心、沉静的悲伤、专注的焦虑、疲惫的倦怠）。
                2. 基于该情绪生成一段100字内的暖心关怀话。
                JSON格式: {{"label":"情绪标签","text":"暖心话","happiness":0.0-1.0,"stress":0.0-1.0}}
                """
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                new_record = {
                    "time": datetime.now().strftime("%H:%M"),
                    "label": data.get("label", "状态平稳"),
                    "message": data.get("text", "..."),
                    "happiness": float(data.get("happiness", 0.5)),
                    "stress": float(data.get("stress", 0.2))
                }
                st.session_state.chat_log.insert(0, new_record)
                st.session_state.last_metrics = new_record
                
                # 系统通知
                js_push = f"<script>window.parent.sendPush('监测提醒：{new_record['label']}', '{new_record['message']}');</script>"
                components.html(js_push, height=0)
            except: pass

    # 左右布局
    col_l, col_r = st.columns([1, 1.2])
    
    with col_l:
        st.subheader("📷 观察窗口")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=300)
        # 实时特征提取模拟
        f_list = ["视线聚焦", "眉心微动", "面部放松", "嘴角微扬"]
        current_f = random.choice(f_list)
        st.session_state.face_log.append(current_f)
        st.info(f"🧬 特征流：{current_f}")

    with col_r:
        st.subheader("📊 实时情感状态")
        
        # 核心情绪显示区
        cur = st.session_state.last_metrics
        st.markdown(f"""
            <div class="status-card">
                <div style="font-size: 0.9em; color: #666;">当前情绪判定</div>
                <div style="font-size: 2em; font-weight: bold; color: #333; margin: 5px 0;">{cur['label']}</div>
                <div style="color: #555; font-style: italic; border-top: 1px solid #eee; padding-top: 10px;">
                    "{cur['message']}"
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 历史简报
        st.write("📜 历史决策简报")
        for chat in st.session_state.chat_log[1:4]: # 显示前3条历史
            st.markdown(f"**[{chat['time']}] {chat['label']}** : {chat['message'][:30]}...")
            
        if st.button("📈 进入大数据分析画面", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据相关性档案")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 多维波动图
        st.write("### 📉 愉悦度与压力波动趋势")
        
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        
        # 情绪标签统计
        st.write("### 🏷️ 情绪频率分析")
        st.bar_chart(df['label'].value_counts())
        
        st.divider()
        st.dataframe(df[["time", "label", "message"]], use_container_width=True)
    else:
        st.warning("数据收集中...")
    
    if st.button("⬅️ 返回监测主站", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
