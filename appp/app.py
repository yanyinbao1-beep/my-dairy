import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 页面与全局状态初始化 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

if "booted" not in st.session_state: st.session_state.booted = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "正在同步", "temp": "20"}
if "mood_score" not in st.session_state: st.session_state.mood_score = 0.5 
if "ai_result" not in st.session_state: 
    st.session_state.ai_result = {"label": "待命中", "analysis": "请面向摄像头", "advice": "比个✌️试试看"}

# --- 2. 情绪动态 UI 引擎 (颜色随心情改变) ---
# 0.0(忧郁) -> 220度(蓝) | 1.0(开心) -> 40度(橘)
hue = 220 - (st.session_state.mood_score * 180)
main_color = f"hsla({hue}, 75%, 60%, 1)"
bg_color = f"radial-gradient(circle at 50% 50%, hsla({hue}, 40%, 12%, 1) 0%, #0a1118 100%)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_color}; color: white; transition: background 2.0s ease; }}
    .glass-card {{
        background: rgba(255, 255, 255, 0.03); border: 1px solid {main_color}44;
        border-radius: 20px; padding: 25px; backdrop-filter: blur(15px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.4);
    }}
    .advice-tag {{
        background: {main_color}15; border-left: 4px solid {main_color};
        padding: 12px; margin-top: 15px; border-radius: 6px; font-size: 0.9em;
    }}
    /* 呆萌扫描封面 */
    #loader {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: #0a1118; display: flex; flex-direction: column;
        align-items: center; justify-content: center; z-index: 9999;
    }}
    .scanner {{
        width: 280px; height: 2px; background: {main_color};
        box-shadow: 0 0 15px {main_color}; animation: scanMove 2s infinite ease-in-out;
    }}
    @keyframes scanMove {{ 0%, 100% {{ transform: translateY(-40px); }} 50% {{ transform: translateY(40px); }} }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 环境传感器：定位与天气 ---
def sync_env():
    try:
        # 多接口备选方案防止“城市未知”
        geo = requests.get("https://ipapi.co/json/", timeout=2).json()
        city = geo.get("city", "上海")
        weather = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo.get('latitude',31)}&longitude={geo.get('longitude',121)}&current_weather=true").json()
        temp = str(weather['current_weather']['temperature'])
        st.session_state.env_data = {"city": city, "temp": temp}
    except:
        st.session_state.env_data = {"city": "上海", "temp": "18"}

# --- 4. 动态启动封面逻辑 ---
if not st.session_state.booted:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
            <div id="loader">
                <div class="scanner"></div>
                <h3 style="color:{main_color}; font-family:monospace; margin-top:30px;">EMO-SYSTEM INITIALIZING...</h3>
            </div>
        """, unsafe_allow_html=True)
        sync_env()
        time.sleep(2.5) # 预留展示时间
    st.session_state.booted = True
    st.rerun()

# --- 5. 暖心 AI 诊断逻辑 ---
def run_ai_analysis():
    if "api_key" not in st.secrets:
        st.error("请在 Secrets 中配置 api_key")
        return
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
    try:
        prompt = f"""
        环境：{st.session_state.env_data['city']}，气温{st.session_state.env_data['temp']}°C。
        结合用户表情(当前心情分约0.5)，给出：
        1. label: 4字状态标签
        2. analysis: 30字情绪画像
        3. advice: 结合当前气温给出一句具体的暖心建议。
        JSON格式返回：{{'label':'','analysis':'','advice':'','score':0.0-1.0}}
        """
        response = client.chat.completions.create(
            model="deepseek-chat", 
            messages=[{"role":"user", "content":prompt}],
            response_format={'type':'json_object'}
        )
        res = json.loads(response.choices[0].message.content)
        st.session_state.ai_result = res
        st.session_state.mood_score = res.get('score', 0.5)
        st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **res})
    except Exception as e:
        st.error(f"AI 引擎诊断中: {e}")

# --- 6. 主界面路由渲染 ---
if st.session_state.current_page == "main":
    # 顶部状态
    st.markdown(f"📍 **{st.session_state.env_data['city']}** | 🌡️ **{st.session_state.env_data['temp']}°C**")
    
    col_v, col_i = st.columns([1.3, 0.7])
    
    with col_v:
        st.subheader("📸 21-Node 实时追踪")
        
        # 核心：MediaPipe 21节点绘制代码
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
                    ctx.save();
                    ctx.clearRect(0,0,c.width,c.height);
                    if(res.multiHandLandmarks && res.multiHandLandmarks.length > 0){{
                        for(const lm of res.multiHandLandmarks){{
                            // 绘制 21 个骨架连线 (绿色)
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {{color:'#00FF00', lineWidth:3}});
                            // 绘制 21 个红色节点
                            drawLandmarks(ctx, lm, {{color:'#FF0000', lineWidth:1, radius:3}});
                            
                            // ✌️ 手势判定：食指中指伸直，无名指收拢
                            if(lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {{
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }}
                        }}
                    }}
                    ctx.restore();
                }});
                
                new Camera(v, {{onFrame:async()=>{{c.width=v.videoWidth; c.height=v.videoHeight; await hands.send({{image:v}});}}}}).start();
            </script>
        """, height=440)
        
        # 跳转触发按钮
        if st.button("📈 开启暖心分析报告", type="primary", use_container_width=True):
            run_ai_analysis()
            st.session_state.current_page = "stats"
            st.rerun()

    with col_i:
        st.subheader("📜 情感画像")
        st.markdown(f"""
            <div class="glass-card">
                <small style="color:{main_color}; font-family:monospace;">STATUS: {st.session_state.ai_result['label']}</small>
                <p style="margin: 15px 0; font-size: 1.1em; line-height: 1.5;">{st.session_state.ai_result['analysis']}</p>
                <div class="advice-tag">
                    <b>💡 暖心贴士：</b><br>{st.session_state.ai_result['advice']}
                </div>
                <div style="margin-top:20px;">
                    <small>情绪能量值</small>
                    <div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:3px; margin-top:8px;">
                        <div style="width:{st.session_state.mood_score*100}%; height:100%; background:{main_color}; box-shadow:0 0 10px {main_color}; transition: 1.5s ease;"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 刷新环境数据"): st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📊 历史感知档案")
    if st.button("⬅️ 返回监测终端"):
        st.session_state.current_page = "main"
        st.rerun()
    
    if st.session_state.chat_log:
        st.table(pd.DataFrame(st.session_state.chat_log).iloc[::-1])
        mood_history = [x['score'] for x in st.session_state.chat_log]
        st.line_chart(mood_history)
