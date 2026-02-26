import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化 (增加类型保护) ---
st.set_page_config(page_title="Emo-Bot 旗舰版", layout="wide")

# 确保所有变量都有正确的初始类型
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"happiness": 0.5, "stress": 0.2, "label": "系统就绪", "message": "等待首次感应..."}

st_autorefresh(interval=10000, key="bot_heartbeat")

# 安全初始化 OpenAI
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except Exception as e:
    st.error("API Key 未配置，请在 Secrets 中设置。")

# --- 2. 增强版通知引擎与 CSS ---
m = st.session_state.last_metrics
# 颜色平滑处理
h_val = 200 - (float(m.get('happiness', 0.5)) * 100)
st.markdown(f"""
    <style>
    .stApp {{ background: hsl({h_val}, 20%, 95%); transition: 3s; }}
    .video-container {{
        width: 100%; aspect-ratio: 4 / 3;
        border: 4px solid #5C6BC0; border-radius: 20px;
        overflow: hidden; background: #000;
    }}
    video {{ width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
    .bot-bubble {{ background: white; border-radius: 15px; padding: 15px; border-left: 5px solid #5C6BC0; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
    </style>
    
    <script>
    // Mac 穿透式通知脚本
    window.parent.activateNotify = function() {{
        if (!("Notification" in window)) {{ alert("浏览器不支持通知"); return; }}
        Notification.requestPermission().then(p => {{
            alert("当前权限状态: " + p + " (若是 denied 请点锁头开启)");
            if (p === "granted") new Notification("✅ 机器人连接成功");
        }});
    }};
    window.parent.sendPush = function(t, b) {{
        if (Notification.permission === 'granted') new Notification(t, {{body: b, icon: 'https://cdn-icons-png.flaticon.com/512/204/204345.png'}});
    }};
    </script>
""", unsafe_allow_html=True)

# --- 3. 页面逻辑 ---

if st.session_state.current_page == "main":
    st.title("🤖 机器人监测站")
    
    # 顶部权限激活区
    if st.button("🔔 第一步：激活 Mac 弹窗权限 (点击后请看系统提示)", use_container_width=True):
        components.html("<script>window.parent.activateNotify();</script>", height=0)

    # 60秒总结逻辑 (增加异常捕获)
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("正在解析情绪..."):
            try:
                prompt = f"特征:{st.session_state.face_log[-6:]}。JSON:{{'text':'暖心话','label':'情绪词','happiness':0.5,'stress':0.2}}"
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                res_content = resp.choices[0].message.content
                if res_content:
                    data = json.loads(res_content)
                    # 关键修复：确保所有键值对都存在，避免 TypeError
                    new_record = {
                        "time": datetime.now().strftime("%H:%M"),
                        "message": data.get("text", "我在听..."),
                        "label": data.get("label", "情绪平稳"),
                        "happiness": float(data.get("happiness", 0.5)),
                        "stress": float(data.get("stress", 0.2))
                    }
                    st.session_state.chat_log.insert(0, new_record)
                    st.session_state.last_metrics = new_record
                    
                    # 发送推送
                    js_code = f"<script>window.parent.sendPush('观察者：{new_record['label']}', '{new_record['message']}');</script>"
                    components.html(js_code, height=0)
            except Exception as e:
                st.warning(f"感应器稍有波动，正在重试...")

    # 布局渲染
    l, r = st.columns([1, 1.2])
    with l:
        st.subheader("📸 实时画面")
        components.html("""
            <div class="video-container"><video id="v" autoplay playsinline></video></div>
            <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
        """, height=300)
        # 模拟特征采集
        feats = ["专注", "平和", "略显疲惫", "若有所思"]
        current_f = random.choice(feats)
        st.session_state.face_log.append(current_f)
        st.info(f"🧬 特征流：{current_f} | 状态：{st.session_state.last_metrics.get('label', '就绪')}")

    with r:
        st.subheader("💬 对话记录")
        # 安全遍历，防止 KeyError/TypeError
        display_log = st.session_state.chat_log[:4]
        if not display_log:
            st.write("等待数据收集中...")
        for chat in display_log:
            st.markdown(f"""
                <div class="bot-bubble">
                    <small>{chat.get('time', '--:--')}</small> <b>{chat.get('label', '分析中')}</b><br>
                    {chat.get('message', '...')}
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("📊 查看数据波动", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 情感大数据")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        st.line_chart(df.set_index("time")[["happiness", "stress"]])
        st.dataframe(df[["time", "label", "message"]], use_container_width=True)
    else:
        st.warning("尚无充足数据进行波动分析。")
    
    if st.button("⬅️ 返回主页", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
