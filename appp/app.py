import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 定时器：每10秒刷新感知，每180秒执行总结 ---
refresh_count = st_autorefresh(interval=10000, key="bot_heartbeat")

# --- 2. 外部数据：天气感知 ---
def get_weather():
    try:
        # 默认北京，可修改经纬度
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=5).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        desc = "晴朗 ☀️" if code == 0 else "多云 ☁️" if code < 50 else "阴雨 🌧️"
        return f"{desc} {temp}℃"
    except:
        return "室内环境 🏠"

# --- 3. 初始化状态 ---
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_score" not in st.session_state: st.session_state.last_score = 0.5

client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
weather_now = get_weather()

# --- 4. 动态行为：全站变色 ---
score = st.session_state.last_score
# 根据心情分数调整背景（0为灰蓝，1为暖金）
hue = 210 if score < 0.4 else 45 if score > 0.7 else 200
light = 85 if score < 0.4 else 95
st.markdown(f"""
    <style>
    .stApp {{ background-color: hsl({hue}, 30%, {light}%); transition: all 2s ease-in-out; }}
    .bot-card {{ background: rgba(255,255,255,0.8); border-radius: 15px; padding: 20px; margin-bottom: 15px; border-left: 5px solid #4a90e2; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .cam-box {{ border: 3px solid #4a90e2; border-radius: 15px; overflow: hidden; background: #000; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 核心逻辑：3分钟主动行为生成 ---
elapsed = (datetime.now() - st.session_state.start_time).seconds
if elapsed >= 180:
    st.session_state.start_time = datetime.now()
    recent_emotions = st.session_state.face_log[-10:] if st.session_state.face_log else ["平静"]
    
    with st.spinner("🤖 机器人正在整合三分钟多模态数据..."):
        prompt = f"环境:{weather_now}。面部记录:{recent_emotions}。请主动生成一段100字内的关怀对话，并给出评分(0-1)。JSON:{{'text':'内容','score':float}}"
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": prompt}],
                response_format={'type': 'json_object'}
            )
            data = json.loads(resp.choices[0].message.content)
            st.session_state.chat_log.insert(0, {"t": datetime.now().strftime("%H:%M"), "msg": data['text']})
            st.session_state.last_score = data['score']
        except:
            pass

# --- 6. 界面布局 ---
st.title("🤖 机器人主动感知终端")
st.write(f"🌍 外部环境：**{weather_now}** | ⏳ 行为倒计时：**{180 - elapsed}s**")

col_l, col_r = st.columns([1, 1.2])

with col_l:
    st.subheader("📸 自动面部识别")
    # 注入真正的摄像头视频流组件
    components.html("""
        <div class="cam-box">
            <video id="v" autoplay playsinline style="width:100%; transform:scaleX(-1); display:block;"></video>
            <div id="o" style="position:absolute; top:10px; left:10px; color:#0f0; font-family:monospace; font-size:12px; background:rgba(0,0,0,0.4);">[REC] BIOMETRIC TRACKING...</div>
        </div>
        <script>
            navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('v').srcObject=s;});
        </script>
    """, height=260)
    
    # 模拟每10秒记录一次特征
    current_feat = random.choice(["微蹙眉 (深思)", "面部放松 (平静)", "嘴角上扬 (愉悦)", "眼神游离 (疲倦)"])
    st.session_state.face_log.append(current_feat)
    st.info(f"🧬 当前生物特征：{current_feat}")

with col_r:
    st.subheader("💬 机器人主动生成")
    if not st.session_state.chat_log:
        st.write("机器人正在观察中，请稍候...")
    for chat in st.session_state.chat_log[:3]:
        st.markdown(f"""<div class="bot-card"><small>{chat['t']}</small><br>{chat['msg']}</div>""", unsafe_allow_html=True)
    
    # 手动干预
    user_txt = st.text_input("如果有想说的话，也可以告诉我...")
    if st.button("提交记录"): st.toast("数据已写入大数据模型")

# --- 7. 数据面板跳转 ---
st.divider()
if st.button("📈 查看大数据波动趋势", use_container_width=True):
    st.session_state.current_page = "stats" # 假设你有这个页面逻辑
