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
st.set_page_config(page_title="Emo-Bot Weather-Link", layout="wide", initial_sidebar_state="collapsed")

if "welcome_finished" not in st.session_state:
    st.session_state.welcome_finished = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {
        "label": "环境同步", "emotion": "扫描中", "happiness": 0.5, "stress": 0.2, 
        "weather_desc": "获取中", "temp": "--", "message": "正在对焦...", "advice": "请保持面部中心对焦"
    }

# --- 2. 经典封面动画 ---
if not st.session_state.welcome_finished:
    st.markdown("""
        <style>
        .stApp { background: #0a0c10; }
        .welcome-box { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 85vh; }
        .loader {
            width: 120px; height: 120px; border: 4px solid #1a1f2b; border-top: 4px solid #5C6BC0;
            border-radius: 50%; animation: spin 1s linear infinite, glow 2s ease-in-out infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes glow { 0%, 100% { box-shadow: 0 0 15px #5C6BC0; } 50% { box-shadow: 0 0 40px #5C6BC0; } }
        .text { margin-top: 40px; color: #5C6BC0; font-family: sans-serif; letter-spacing: 8px; font-size: 18px; }
        </style>
        <div class="welcome-box"><div class="loader"></div><div class="text">EMO-BOT INITIALIZING</div></div>
    """, unsafe_allow_html=True)
    time.sleep(2.2); st.session_state.welcome_finished = True; st.rerun()

# --- 3. 核心功能 ---
else:
    st_autorefresh(interval=10000, key="bot_heartbeat")
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

    # [增强天气获取]
    @st.cache_data(ttl=1800)
    def get_detailed_context():
        try:
            geo = requests.get("http://ip-api.com/json/", timeout=3).json()
            city = geo.get("city", "未知地区")
            w_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('lat',39.9)}&longitude={geo.get('lon',116.4)}&current_weather=true", timeout=3).json()
            code = w_res['current_weather']['weathercode']
            # 天气代码映射与UI氛围参数
            w_map = {0: ("晴朗", 20), 1: ("微云", 15), 2: ("多云", 10), 3: ("阴天", 5), 61: ("雨天", 2), 95: ("雷雨", 0)}
            desc, saturation_boost = w_map.get(code, ("多云", 10))
            return city, desc, w_res['current_weather']['temperature'], saturation_boost
        except: return "本地", "晴朗", 25.0, 15

    city_name, weather_desc, temp_val, sat_boost = get_detailed_context()

    # [UI 氛围与背景逻辑]
    m = st.session_state.last_metrics
    h_val = 210 - (float(m.get('happiness', 0.5)) * 100)
    # 饱和度随天气调整：晴天更鲜艳，阴天更灰暗
    s_val = 10 + sat_boost 
    
    st.markdown(f"""
        <style>
        .stApp {{ background: hsl({h_val}, {s_val}%, 96%); transition: 4s ease-in-out; }}
        .video-container {{
            width: 100%; position: relative; padding-top: 75%; border: 3px solid #5C6BC0; 
            border-radius: 20px; overflow: hidden; background: #000;
        }}
        video {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }}
        .focus-ring {{
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 60%; height: 75%; border: 2px dashed rgba(92, 107, 192, 0.4);
            border-radius: 40% 40% 50% 50%; pointer-events: none;
        }}
        .status-card {{
            background: rgba(255, 255, 255, 0.9); border-radius: 24px; padding: 25px;
            border-left: 12px solid hsl({h_val}, 60%, 50%);
            box-shadow: 0 12px 30px rgba(0,0,0,0.08); min-height: 420px;
        }}
        .weather-chip {{
            background: #1a1a1a; color: #fff; padding: 5px 15px; border-radius: 20px; font-size: 13px;
        }}
        .advice-box {{ background: hsl({h_val}, 30%, 98%); border-radius: 15px; padding: 18px; margin-top: 20px; border: 1px dashed #5C6BC0; }}
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.current_page == "main":
        # 顶部栏
        header_col, info_col = st.columns([3, 1])
        with header_col: st.title("🤖 深度情绪监测站")
        with info_col: 
            st.markdown(f"<div style='text-align:right'><span class='weather-chip'>📍 {city_name} | {weather_desc} {temp_val}℃</span></div>", unsafe_allow_html=True)

        # [深度天气 AI 逻辑]
        elapsed = (datetime.now() - st.session_state.start_time).seconds
        if elapsed >= 60 or not st.session_state.chat_log:
            st.session_state.start_time = datetime.now()
            try:
                prompt = f"""
                当前环境：{city_name}, 天气：{weather_desc}, 温度：{temp_val}℃。
                任务：结合天气对摄像头前的人物进行情绪推演。
                JSON格式：
                {{
                    "label": "4字环境总结",
                    "emotion": "具体心理词",
                    "text": "30字感悟（需体现天气对心境的影响）",
                    "advice": "针对该天气和情绪的15字建议",
                    "happiness": 0.0-1.0, "stress": 0.0-1.0
                }}
                """
                resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}], response_format={'type': 'json_object'})
                data = json.loads(resp.choices[0].message.content)
                record = {
                    "time": datetime.now().strftime("%H:%M"), "label": data.get("label"), 
                    "emotion": data.get("emotion"), "message": data.get("text"), "advice": data.get("advice"),
                    "happiness": float(data.get("happiness", 0.5)), "stress": float(data.get("stress", 0.2)),
                    "weather": weather_desc, "temp": temp_val
                }
                st.session_state.chat_log.insert(0, record); st.session_state.last_metrics = record
            except: pass

        col_v, col_i = st.columns([4.5, 5.5])
        with col_v:
            st.subheader("📸 视觉特征采集")
            components.html("""
                <div class="video-container"><video id="v" autoplay playsinline></video><div class="focus-ring"></div></div>
                <script>navigator.mediaDevices.getUserMedia({video: {aspectRatio: 1.333}}).then(s => {document.getElementById('v').srcObject = s;});</script>
            """, height=380)
            st.caption(f"系统：当前{weather_desc}氛围已载入，人物特征居中对焦中")

        with col_i:
            st.subheader("📊 实时推演")
            cur = st.session_state.last_metrics
            # 使用 Markdown + HTML 渲染卡片
            st.markdown(f"""
                <div class='status-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h2 style='color:#1A237E; margin:0;'>{cur.get('label')}</h2>
                        <span style='color:#888; font-size:12px;'>SYNC: {cur.get('time')}</span>
                    </div>
                    <div style='margin-top: 15px;'>
                        <span style='background:#5C6BC0; color:white; padding:5px 15px; border-radius:30px; font-weight:bold; font-size:14px;'>
                            感知情绪：{cur.get('emotion')}
                        </span>
                    </div>
                    <div style='margin-top:25px; font-size:18px; color:#2c3e50; line-height:1.6; font-family:serif;'>
                        “{cur.get('message')}”
                    </div>
                    <div class='advice-box'>
                        <b style='color:#5C6BC0;'>💡 结合{cur.get('weather','环境')}的建议：</b><br>
                        <span style='color:#444; font-size:15px;'>{cur.get('advice')}</span>
                    </div>
                    <div style='margin-top:30px;'>
                        <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                            <small style='color:#666;'>愉悦感指数</small> 
                            <small style='font-weight:bold; color:#5C6BC0;'>{int(cur.get('happiness')*100)}%</small>
                        </div>
                        <div style='background:#eee; height:8px; border-radius:4px;'>
                            <div style='background:linear-gradient(90deg, #5C6BC0, #8E99F3); width:{cur.get('happiness')*100}%; height:8px; border-radius:4px; transition:2s;'></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("查看历史环境轨迹记录", use_container_width=True):
                st.session_state.current_page = "stats"; st.rerun()

    elif st.session_state.current_page == "stats":
        st.title("📊 环境与情绪关联轨迹")
        if st.session_state.chat_log:
            df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
            st.line_chart(df.set_index("time")[["happiness", "stress"]])
            st.dataframe(df[["time", "weather", "temp", "emotion", "advice", "label"]], use_container_width=True, hide_index=True)
        st.button("⬅️ 返回主控台", on_click=lambda: st.session_state.update({"current_page":"main"}))
