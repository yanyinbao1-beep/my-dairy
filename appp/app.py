import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 基础配置与动态色彩 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

if "booted" not in st.session_state: st.session_state.booted = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "定位中", "temp": "20"}
if "mood_score" not in st.session_state: st.session_state.mood_score = 0.5

hue = 220 - (st.session_state.mood_score * 180)
main_color = f"hsla({hue}, 70%, 60%, 1)"

st.markdown(f"""
    <style>
    .stApp {{ background: radial-gradient(circle at 50% 50%, hsla({hue}, 40%, 10%, 1) 0%, #0a1118 100%); color: white; transition: 1.5s; }}
    .glass-card {{ background: rgba(255,255,255,0.03); border: 1px solid {main_color}44; border-radius: 20px; padding: 25px; backdrop-filter: blur(10px); }}
    #loader {{ position: fixed; top:0; left:0; width:100%; height:100%; background:#0a1118; z-index:9999; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
    .scan-line {{ width:260px; height:2px; background:{main_color}; box-shadow:0 0 15px {main_color}; animation: scan 2s infinite; }}
    @keyframes scan {{ 0%,100% {{transform:translateY(-40px);}} 50% {{transform:translateY(40px);}} }}
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心功能：多源定位方案 ---
def fetch_location():
    # 依次尝试三个不同的定位接口，解决“城市未知”
    urls = [
        "https://ipapi.co/json/",
        "https://api.ip.sb/geoip",
        "https://freeipapi.com/api/json"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=2).json()
            city = res.get("city") or res.get("cityName") or "北京"
            lat = res.get("latitude") or res.get("latitude") or 39.9
            lon = res.get("longitude") or res.get("longitude") or 116.4
            # 获取天气
            w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=2).json()
            st.session_state.env_data = {"city": city, "temp": str(w['current_weather']['temperature'])}
            return
        except: continue
    st.session_state.env_data = {"city": "上海", "temp": "18"} # 最终兜底

# --- 3. 动态封面 ---
if not st.session_state.booted:
    cp = st.empty()
    with cp.container():
        st.markdown(f'<div id="loader"><div class="scan-line"></div><h3 style="color:{main_color};margin-top:20px;">SYSTEM STARTING...</h3></div>', unsafe_allow_html=True)
        fetch_location()
        time.sleep(2)
    st.session_state.booted = True
    st.rerun()

# --- 4. 主界面 ---
if st.session_state.current_page == "main":
    st.markdown(f"📍 {st.session_state.env_data['city']} | {st.session_state.env_data['temp']}°C")
    
    col_v, col_i = st.columns([1.3, 0.7])
    
    with col_v:
        st.subheader("📸 实时 21 节点追踪")
        
        components.html(f"""
            <div style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:20px; border:2px solid {main_color}; overflow:hidden;">
                <video id="v" style="width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="c" style="position:absolute; top:0; left:0; width:100%; height:100%; transform:scaleX(-1);"></canvas>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
            <script>
                const v=document.getElementById('v'), c=document.getElementById('c'), ctx=c.getContext('2d');
                const hands=new Hands({{locateFile:(f)=>`https://cdn.jsdelivr.net/npm/@mediapipe/hands/${{f}}`}});
                hands.setOptions({{maxNumHands:1, modelComplexity:1, minDetectionConfidence:0.5}});
                hands.onResults((res)=>{{
                    ctx.clearRect(0,0,c.width,c.height);
                    if(res.multiHandLandmarks){{
                        for(const lm of res.multiHandLandmarks){{
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {{color:'#00FF00', lineWidth:2}});
                            drawLandmarks(ctx, lm, {{color:'#FF0000', radius:3}});
                            // ✌️ 判定跳转 (极速触发)
                            if(lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {{
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }}
                        }}
                    }}
                }});
                new Camera(v,{{onFrame:async()=>{{c.width=v.videoWidth; c.height=v.videoHeight; await hands.send({{image:v}});}}}}).start();
            </script>
        """, height=450)
        
        # 极速触发按钮：先跳转，不在此处调用 AI
        if st.button("📈 启动深度感知分析", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.markdown(f'<div class="glass-card"><h3>系统就绪</h3><p>在视频中比出 ✌️ 手势，系统将结合 <b>{st.session_state.env_data["city"]}</b> 的天气为你生成暖心建议。</p></div>', unsafe_allow_html=True)

# --- 5. 分析页面（异步执行 AI 逻辑） ---
elif st.session_state.current_page == "stats":
    st.title("📈 正在为您生成暖心分析...")
    
    # 模拟异步 AI 加载效果
    with st.spinner("AI 正在根据天气与表情进行深度诊断..."):
        client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
        try:
            p = f"城市{st.session_state.env_data['city']}，气温{st.session_state.env_data['temp']}°C。结合心情score(0.5)给出4字标签、30字分析和建议。JSON:{{'label':'','analysis':'','advice':'','score':0.6}}"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p}], response_format={'type':'json_object'})
            data = json.loads(r.choices[0].message.content)
            st.session_state.mood_score = data['score']
            st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **data})
            
            # 显示结果卡片
            st.markdown(f"""
                <div class="glass-card">
                    <h2 style="color:{main_color}">{data['label']}</h2>
                    <p>{data['analysis']}</p>
                    <div style="background:{main_color}22; padding:15px; border-left:4px solid {main_color}; border-radius:10px;">
                        <b>💡 暖心建议：</b><br>{data['advice']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error("AI 引擎暂时走神了...")

    if st.button("⬅️ 返回监测台", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()

    if st.session_state.chat_log:
        st.subheader("📜 历史感知档案")
        st.table(pd.DataFrame(st.session_state.chat_log).iloc[::-1])
