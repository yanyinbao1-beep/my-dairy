import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import time

# --- 1. 基础配置 ---
st.set_page_config(page_title="Emo-Bot 感知终端", layout="wide", initial_sidebar_state="collapsed")

if "booted" not in st.session_state: st.session_state.booted = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "获取中...", "temp": "15"}
if "mood_score" not in st.session_state: st.session_state.mood_score = 0.5 
if "ai_result" not in st.session_state: 
    st.session_state.ai_result = {"label": "待机中", "analysis": "正在等待捕捉你的神情...", "advice": "比个✌️试试？"}

# --- 2. 情绪动态 UI 引擎 ---
hue = 220 - (st.session_state.mood_score * 180)
main_color = f"hsla({hue}, 70%, 60%, 1)"

st.markdown(f"""
    <style>
    .stApp {{ background: radial-gradient(circle at 50% 50%, hsla({hue}, 40%, 10%, 1) 0%, #0a1118 100%); color: white; transition: 2s; }}
    .glass-card {{
        background: rgba(255, 255, 255, 0.03); border: 1px solid {main_color}55;
        border-radius: 20px; padding: 25px; backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px;
    }}
    .advice-tag {{
        background: {main_color}22; border-left: 4px solid {main_color};
        padding: 10px 15px; margin-top: 15px; border-radius: 4px; font-style: italic;
    }}
    /* 动态封面 */
    #loading-cover {{ position: fixed; top:0; left:0; width:100%; height:100%; background:#0a1118; z-index:9999; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
    .scan-bar {{ width:250px; height:2px; background:{main_color}; box-shadow:0 0 15px {main_color}; animation: scan 2s infinite; }}
    @keyframes scan {{ 0%,100% {{transform:translateY(-40px); opacity:0.2;}} 50% {{transform:translateY(40px); opacity:1;}} }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心功能：定位与暖心 AI ---
def get_env():
    try:
        geo = requests.get("https://ipapi.co/json/", timeout=3).json()
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo['latitude']}&longitude={geo['longitude']}&current_weather=true").json()
        st.session_state.env_data = {"city": geo['city'], "temp": str(w['current_weather']['temperature'])}
    except: st.session_state.env_data = {"city": "地球某处", "temp": "22"}

def run_warm_analysis():
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
    try:
        # 强化 Prompt：要求结合天气提供暖心建议
        prompt = f"""
        用户位置：{st.session_state.env_data['city']}，气温：{st.session_state.env_data['temp']}°C。
        请作为暖心的情绪伴侣，结合天气和检测到的神情（score反映：0忧郁，1开心），提供分析。
        要求：
        1. analysis: 30字内描述用户当前的情绪状态。
        2. advice: 根据天气给出一句具体的暖心生活建议。
        3. label: 一个4字状态标签。
        JSON格式返回：{{'label':'','analysis':'','advice':'','score':0.0-1.0}}
        """
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.ai_result = data
        st.session_state.mood_score = data.get('score', 0.5)
        st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **data})
    except: pass

# --- 4. 动态封面 ---
if not st.session_state.booted:
    cp = st.empty()
    with cp.container():
        st.markdown(f'<div id="loading-cover"><div class="scan-bar"></div><h3 style="color:{main_color};margin-top:20px;">感知系统启动中...</h3></div>', unsafe_allow_html=True)
        get_env()
        time.sleep(2.5)
    st.session_state.booted = True
    cp.empty()

# --- 5. 页面渲染 ---
if st.session_state.current_page == "main":
    st.markdown(f"📍 **{st.session_state.env_data['city']}** · {st.session_state.env_data['temp']}°C")
    
    col_v, col_i = st.columns([1.3, 0.7])
    
    with col_v:
        st.subheader("📸 视觉节点监测")
        
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
                hands.setOptions({{maxNumHands:1, minDetectionConfidence:0.5}});
                hands.onResults((res)=>{{
                    ctx.clearRect(0,0,c.width,c.height);
                    if(res.multiHandLandmarks){{
                        for(const lm of res.multiHandLandmarks){{
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {{color:'#00FF00', lineWidth:2}});
                            drawLandmarks(ctx, lm, {{color:'#FF0000', radius:3}});
                            if(lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {{
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }}
                        }}
                    }}
                }});
                new Camera(v,{{onFrame:async()=>{{c.width=v.videoWidth; c.height=v.videoHeight; await hands.send({{image:v}});}}}}).start();
            </script>
        """, height=450)
        
        if st.button("📈 开启暖心分析", type="primary", use_container_width=True):
            run_warm_analysis()
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📜 今日感知报告")
        st.markdown(f"""
            <div class="glass-card">
                <span style="color:{main_color}; font-family:monospace;">STATUS: {st.session_state.ai_result.get('label','待机')}</span>
                <h3 style="margin:10px 0;">表情映射分析</h3>
                <p style="font-size:0.95em; line-height:1.5; color:#eee;">{st.session_state.ai_result.get('analysis')}</p>
                <div class="advice-tag">
                    <b>💡 暖心建议：</b><br>{st.session_state.ai_result.get('advice')}
                </div>
                <div style="margin-top:20px;">
                    <small>情绪能量值</small>
                    <div style="width:100%; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; margin-top:8px;">
                        <div style="width:{st.session_state.mood_score*100}%; height:100%; background:{main_color}; box-shadow:0 0 10px {main_color}; transition:1.5s;"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 刷新环境"): st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📈 情绪历史档案")
    if st.button("⬅️ 返回监测台"):
        st.session_state.current_page = "main"
        st.rerun()
    if st.session_state.chat_log:
        st.table(pd.DataFrame(st.session_state.chat_log).iloc[::-1])
