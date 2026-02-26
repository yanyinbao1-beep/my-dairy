import streamlit as st
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import random  # <--- 确保加上这一行
# --- 1. 自动刷新配置：每 10 秒刷新一次界面以保持感知，每 180 秒执行一次大总结 ---
# 逻辑：每 10 秒刷新同步一次面部数据，计数达到 18 次（3分钟）触发 AI 对话
refresh_count = st_autorefresh(interval=10000, key="sensing_loop")

# --- 2. 外部数据接入：Open-Meteo 天气 ---
def get_real_weather():
    try:
        # 以北京坐标为例 (经度: 116.4, 纬度: 39.9)
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        response = requests.get(url).json()
        temp = response['current_weather']['temperature']
        code = response['current_weather']['weathercode']
        # 简单天气码映射
        weather_desc = "晴朗 ☀️" if code == 0 else "多云 ☁️" if code < 50 else "小雨 🌧️"
        return f"{weather_desc} {temp}℃"
    except:
        return "环境感知异常 📡"

# --- 3. 初始化全局状态 ---
if "face_history" not in st.session_state: st.session_state.face_history = [] # 存储短周期表情
if "chat_history" not in st.session_state: st.session_state.chat_history = [] # 存储机器人对话
if "last_summary_time" not in st.session_state: st.session_state.last_summary_time = datetime.now()

client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 4. 视觉层：随环境变色 ---
weather_info = get_real_weather()
score = st.session_state.get('last_score', 0.5)
bg_color = "#f0f2f6" if "晴" in weather_info else "#e1e5eb"
if score < 0.4: bg_color = "#d1d9e6" # 忧郁模式

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; transition: all 1s; }}
    .bot-bubble {{ 
        background: white; border-radius: 15px; padding: 15px; 
        border-left: 5px solid #4A90E2; margin: 10px 0;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 核心：三分钟总结逻辑 (主动行为生成) ---
time_since_last = (datetime.now() - st.session_state.last_summary_time).seconds

if time_since_last >= 180: # 180秒 = 3分钟
    st.session_state.last_summary_time = datetime.now()
    # 提取最近三分钟的表情倾向
    recent_faces = st.session_state.face_history[-10:] if st.session_state.face_history else ["平静"]
    
    # 机器人主动发起对话
    with st.spinner("🤖 机器人正在生成三分钟阶段性总结..."):
        prompt = f"""
        你是情绪分析机器人。过去3分钟环境：{weather_info}。
        观察到的用户微表情序列：{recent_faces}。
        请结合环境和表情，主动说一句话跟用户交流，并给出一个0-1的情绪评分。
        JSON: {{"dialogue": "内容", "score": float}}
        """
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": prompt}],
            response_format={'type': 'json_object'}
        )
        res = json.loads(response.choices[0].message.content)
        st.session_state.chat_history.insert(0, {"time": datetime.now().strftime("%H:%M"), "text": res['dialogue']})
        st.session_state.last_score = res['score']

# --- 6. 界面布局 ---
st.title("🤖 智能感知机器人终端")
st.caption(f"当前时空数据：{weather_info} | 距离下次主动总结：{180 - time_since_last}s")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📸 实时生物监测")
    # 模拟面部识别反馈
    current_face = random.choice(["专注", "平静", "微笑", "深思"])
    st.session_state.face_history.append(current_face)
    
    st.info(f"当前识别特征：{current_face}")
    st.progress(time_since_last / 180, text="行为生成倒计时")
    
    # 艺术表达占位
    st.markdown('<div style="height:200px; border:2px dashed #ccc; display:flex; align-items:center; justify-content:center;">🖼️ 艺术生成模块待命</div>', unsafe_allow_html=True)

with col_right:
    st.subheader("💬 机器人对话记录")
    for chat in st.session_state.chat_history[:5]:
        st.markdown(f"""
            <div class="bot-bubble">
                <small style="color:#888;">{chat['time']} 机器人主动发起：</small><br>
                {chat['text']}
            </div>
        """, unsafe_allow_html=True)
    
    # 交互日记区
    diary_input = st.text_area("在此手动输入心语 (选填)...", height=100)
    if st.button("手动存入"):
        st.success("数据已存入大数据池。")

# --- 7. 数据历史 ---
with st.expander("📊 大数据情感波动档案"):
    if st.session_state.face_history:
        st.line_chart(pd.DataFrame({"表情活跃度": [len(f) for f in st.session_state.face_history]}))
