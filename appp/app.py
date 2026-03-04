import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
import time
from streamlit_autorefresh import st_autorefresh

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot Pro v2", layout="wide", initial_sidebar_state="collapsed")

# 初始化 Session State
if "welcome_finished" not in st.session_state:
    st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "系统待命", "happiness": 0.5, "stress": 0.2, 
        "weather": "定位中...", "temp": "--", "message": "正在连接神经元集群..."
    }

# --- 2. 启动动画 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a0c10; }
        .welcome-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .loader {
            width: 100px; height: 100px; border: 3px solid #1a1f2b; border-top: 3px solid #5C6BC0;
            border-radius: 50%; animation: spin 0.8s linear infinite, glow 2s ease-in-out infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 20px #5C6BC0; } 50% { box-shadow: 0 0 50px #5C6BC0; } }
        .text { margin-top: 40px; color: #5C6BC0; font-family: monospace; letter-spacing: 5px; font-size: 16px; }
        </style>
        <div class="welcome-box"><div class="loader"></div><div class="text">EMO-BOT INITIALIZING...</div></div>
    """, unsafe_allow_html=True)
    time.sleep(1.8) 
    st.session_state.welcome_finished = True
    st.rerun()

# --- 3. 核心功能逻辑 ---
else:
    # 设置心跳，每 10 秒刷新一次以检查 AI 更新计时
    st_autorefresh(interval=10000, key="bot_heartbeat")
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

    # [定位与天气接口]
    @st.cache_data(ttl=1800)
    def get_context_data():
        try:
            geo = requests.get("http://ip-api.com/json/", timeout=3).json()
            city = geo.get("city", "未知地区")
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true"
            w_res = requests.get(w_url, timeout=3).json()
            temp = w_res['current_weather']['temperature']
            w_map = {0: "晴朗", 1: "微云", 2: "多云", 3: "阴天", 61: "小雨", 95: "雷阵雨"}
            return f"{city} | {w_map.get(w_res['current_weather']['weathercode'], '多云')}", temp
        except: return "局域网环境", 24.0

    current_weather, current_temp = get_context_data()

    # [全局样式：根据情绪改变背景色]
    m = st.session_state.last_metrics
    h_val = 210 - (float(m.get('happiness', 0.5)) * 120) # 快乐则偏蓝绿，压抑则偏紫红
    st.markdown(f"""
        <style>
        .stApp {{ background: hsl({h_val}, 15%, 96%); transition: background 3s ease; }}
        .video-container {{
            width: 100%; position: relative; padding-top: 75%; /* 锁定 4:3 比例 */
            border: 3px solid #5C6BC0; border-radius: 20px;
            overflow: hidden; background: #000; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        video {{ 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            object-fit: cover; transform: scaleX(-1); 
        }}
        .status-card {{
            background: white; border-radius: 20px; padding: 30px;
            border-left: 10px solid hsl({h_val}, 60%, 50%);
            box-shadow: 0 15px 35px rgba(0,0,0,0.05); min-height: 280px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 页面内容 ---
    if st.session_state.current_page == "main":
        t1, t2 = st.columns([3, 1])
        with t1: st.title("🤖 深度情绪监测站")
        with t2: st.info(f"📍 {current_weather}  🌡️ {current_temp}℃")

        # [AI 自动推演逻辑]
        elapsed = (datetime.now() - st.session_state.start_time).seconds
        if elapsed >= 60 or not st.session_state.chat_log:
            st.session_state.start_time = datetime.now()
            try:
                styles = ["赛博朋克观察者", "温柔治愈师", "存在主义哲学家", "硬核心理医生", "浪漫诗人"]
                target_style = random.choice(styles)
                
                prompt = f"""
                环境：{current_weather}, 温度：{current_temp}℃。
                角色：请以【{target_style}】的视角分析。
                返回JSON:
                {{
                    "label": "4字精炼标签",
                    "text": "一句30字内深度评论",
                    "happiness": 0.0-1.0随机数,
                    "stress": 0.0-1.0随机数
                }}
                """
                resp = client.chat.completions.create(
                    model="deepseek-chat", 
                    messages=[{"role": "user", "content": prompt}], 
                    response_format={'type': 'json_object'},
                    temperature=1.2
                )
                data = json.loads(resp.choices[0].message.content)
                record = {
                    "time": datetime.now().strftime("%H:%M"), "label": data.get("label"), 
                    "message": data.get("text"), "happiness": float(data.get("happiness", 0.5)), 
                    "stress": float(data.get("stress", 0.2)), "weather": current_weather, "temp": current_temp
                }
                st.session_state.chat_log.insert(0, record)
                st.session_state.last_metrics = record
            except: pass

        # [核心布局 4:6]
        col_v, col_i = st.columns([4, 6])
        
        with col_v:
            st.subheader("📸 实时采集 (4:3)")
            components.html("""
                <div class="video-container"><video id="v" autoplay playsinline></video></div>
                <script>
                navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.3333}}).then(s => {
                    document.getElementById('v').srcObject = s;
                });
                </script>
            """, height=380)
            st.caption("系统正在提取微表情特征流...")

        with col_i:
            st.subheader("📊 实时推演结果")
            cur = st.session_state.last_metrics
            st.markdown(f"""
                <div class='status-card'>
                    <small style='color:#888; font-weight:bold;'>Style: {random.choice(['Neural Analysis', 'Deep Insight', 'Bio-Metric'])}</small>
                    <h2 style='color:#1A237E; margin: 15px 0;'>{cur.get('label')}</h2>
                    <div style='border-top:2px solid #f0f0f0; padding-top:20px; font-size:1.2rem; color:#444; font-style:italic;'>
                        “{cur.get('message')}”
                    </div>
                    <div style='margin-top:30px; display:flex; gap:20px;'>
                        <div style='flex:1'>
                            <small>愉悦感</small>
                            <div style='background:#eee; height:8px; border-radius:4px;'>
                                <div style='background:#4CAF50; width:{cur.get('happiness')*100}%; height:8px; border-radius:4px;'></div>
                            </div>
                        </div>
                        <div style='flex:1'>
                            <small>压力值</small>
                            <div style='background:#eee; height:8px; border-radius:4px;'>
                                <div style='background:#F44336; width:{cur.get('stress')*100}%; height:8px; border-radius:4px;'></div>
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("📈 展开历史大数据看板", use_container_width=True):
                st.session_state.current_page = "stats"
                st.rerun()

    elif st.session_state.current_page == "stats":
        st.title("📊 情感轨迹大数据分析")
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("### 📉 情绪波动趋势")
                st.line_chart(df.set_index("time")[["happiness", "stress"]])
            with c2:
                st.write("### 🌡️ 环境气温关联")
                st.area_chart(df.set_index("time")["temp"])

            st.write("### 📑 历史深度监测记录")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("暂无数据记录")
        
        if st.button("⬅️ 返回主控台", use_container_width=True):
            st.session_state.current_page = "main"
            st.rerun()
