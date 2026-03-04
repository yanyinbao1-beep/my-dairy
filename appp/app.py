import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 核心配置与全局样式 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 状态初始化
if "booted" not in st.session_state: st.session_state.booted = False
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "env_data" not in st.session_state: st.session_state.env_data = {"city": "未知", "temp": "20"}
if "mood_score" not in st.session_state: st.session_state.mood_score = 0.5 
if "ai_result" not in st.session_state: 
    st.session_state.ai_result = {"label": "待命", "analysis": "等待系统扫描...", "advice": "请在镜头前比个 ✌️"}

# 根据心情分数计算 HSLA 颜色 (0.0=蓝, 1.0=橙)
hue = 220 - (st.session_state.mood_score * 180)
main_color = f"hsla({hue}, 70%, 60%, 1)"
bg_gradient = f"radial-gradient(circle at 50% 50%, hsla({hue}, 40%, 12%, 1) 0%, #0a1118 100%)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_gradient}; color: white; transition: background 2s ease; }}
    
    /* 玻璃态卡片 */
    .glass-card {{
        background: rgba(255, 255, 255, 0.03); border: 1px solid {main_color}44;
        border-radius: 20px; padding: 25px; backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.4); margin-bottom: 20px;
    }}
    
    .advice-tag {{
        background: {main_color}15; border-left: 4px solid {main_color};
        padding: 12px 18px; margin-top: 15px; border-radius: 6px; 
        font-size: 0.95em; line-height: 1.6; color: #eee;
    }}

    /* 动态启动封面 */
    #loader-screen {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: #0a1118; display: flex; flex-direction: column;
        align-items: center; justify-content: center; z-index: 9999;
    }}
    .scan-line {{
        width: 300px; height: 2px; background: {main_color};
        box-shadow: 0 0 20px {main_color};
        animation: scanMove 2.5s infinite ease-in-out;
    }}
    @keyframes scanMove {{ 
        0%, 100% {{ transform: translateY(-60px); opacity: 0.2; }} 
        50% {{ transform: translateY(60px); opacity: 1; }} 
    }}
    
    /* 按钮美化 */
    .stButton>button {{
        background: transparent; border: 1px solid {main_color}; color: white;
        border-radius: 40px; transition: 0.4s; width: 100%;
    }}
    .stButton>button:hover {{ background: {main_color}; box-shadow: 0 0 15px {main_color}; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. 自动化逻辑：定位与 AI 分析 ---
def sync_environment():
    """获取精准地理位置和天气"""
    try:
        geo = requests.get("https://ipapi.co/json/", timeout=3).json()
        city = geo.get("city", "上海")
        weather = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={geo['latitude']}&longitude={geo['longitude']}&current_weather=true").json()
        temp = str(weather['current_weather']['temperature'])
        st.session_state.env_data = {"city": city, "temp": temp}
    except:
        st.session_state.env_data = {"city": "未知城市", "temp": "22"}

def run_warm_ai_agent():
    """深度融合天气与情绪的暖心分析"""
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
    try:
        prompt = f"""
        用户目前在{st.session_state.env_data['city']}，当地气温为{st.session_state.env_data['temp']}°C。
        请结合这些环境因素和用户此时的心情得分（score: 0.0忧郁到1.0快乐），
        生成：1. 一个4字标签；2. 一段30字的情绪画像分析；3. 一句结合天气的暖心关怀建议。
        严格返回 JSON: {{'label':'','analysis':'','advice':'','score':0.5}}
        """
        resp = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
        data = json.loads(resp.choices[0].message.content)
        st.session_state.ai_result = data
        st.session_state.mood_score = data.get('score', 0.5)
        st.session_state.chat_log.append({"time": datetime.now().strftime("%H:%M"), **data})
    except Exception as e:
        st.error(f"AI 引擎连接异常: {e}")

# --- 3. 动态封面逻辑 ---
if not st.session_state.booted:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
            <div id="loader-screen">
                <div class="scan-line"></div>
                <h2 style="color:{main_color}; font-family:monospace; margin-top:30px; letter-spacing:5px;">SYSTEM BOOTING</h2>
                <p style="color:#555; font-size:0.8em;">SYNCING BIOMETRIC NODES & ENVIRONMENTAL DATA</p>
            </div>
        """, unsafe_allow_html=True)
        sync_environment()
        time.sleep(3)
    st.session_state.booted = True
    st.rerun()

# --- 4. 界面布局与 21 节点追踪 ---
if st.session_state.current_page == "main":
    # 顶部状态
    st.markdown(f"🛰️ **SENSOR ACTIVE** | 📍 {st.session_state.env_data['city']} | 🌡️ {st.session_state.env_data['temp']}°C")
    
    col_cam, col_info = st.columns([1.3, 0.7])
    
    with col_cam:
        st.subheader("📸 实时手势关键点追踪")
        
        # 强制绘制节点和骨架的核心代码
        components.html(f"""
            <div style="position:relative; width:100%; aspect-ratio:4/3; background:#000; border-radius:24px; border:3px solid {main_color}; overflow:hidden; box-shadow: 0 0 20px {main_color}44;">
                <video id="webcam" style="position:absolute; width:100%; height:100%; object-fit:cover; transform:scaleX(-1);" autoplay playsinline></video>
                <canvas id="canvas" style="position:absolute; width:100%; height:100%; transform:scaleX(-1);"></canvas>
                <div id="status-tag" style="position:absolute; top:15px; left:15px; color:#0F0; font-family:monospace; font-size:12px; background:rgba(0,0,0,0.6); padding:4px 8px; border-radius:4px; border:1px solid #0F0;">VISION: OK</div>
            </div>

            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>

            <script>
                const video = document.getElementById('webcam');
                const canvas = document.getElementById('canvas');
                const ctx = canvas.getContext('2d');
                const status = document.getElementById('status-tag');

                const hands = new Hands({{locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${{file}}`}});
                hands.setOptions({{ maxNumHands: 1, modelComplexity: 1, minDetectionConfidence: 0.6, minTrackingConfidence: 0.6 }});

                function onResults(results) {{
                    ctx.save();
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {{
                        status.innerText = "TRACKING: 21 NODES FOUND";
                        status.style.color = "#0F0";
                        for (const landmarks of results.multiHandLandmarks) {{
                            // 强制绘制 21 个骨架连线
                            drawConnectors(ctx, landmarks, HAND_CONNECTIONS, {{color: '#00FF00', lineWidth: 3}});
                            // 强制绘制 21 个红色坐标点
                            drawLandmarks(ctx, landmarks, {{color: '#FF0000', lineWidth: 1, radius: 4}});
                            
                            // ✌️ 手势判定逻辑
                            const indexUp = landmarks[8].y < landmarks[6].y;
                            const middleUp = landmarks[12].y < landmarks[10].y;
                            const ringDown = landmarks[16].y > landmarks[14].y;
                            if (indexUp && middleUp && ringDown) {{
                                status.innerText = "GESTURE: VICTORY DETECTED";
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }}
                        }}
                    }} else {{
                        status.innerText = "SEARCHING FOR HAND...";
                        status.style.color = "#FF0";
                    }}
                    ctx.restore();
                }}

                hands.onResults(onResults);

                new Camera(video, {{
                    onFrame: async () => {{
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        await hands.send({{image: video}});
                    }}
                }}).start();
            </script>
        """, height=460)
        
        # 触发分析的隐形/显性按钮
        if st.button("📈 开启深度情绪与天气分析", type="primary", use_container_width=True):
            run_warm_ai_agent()
            st.session_state.current_page = "stats"
            st.rerun()

    with col_info:
        st.subheader("📜 情感感知报告")
        st.markdown(f"""
            <div class="glass-card">
                <p style="color:{main_color}; font-family:monospace; font-weight:bold; letter-spacing:2px;">
                    {st.session_state.ai_result['label']}
                </p>
                <p style="margin: 15px 0; font-size: 1.05em; line-height:1.4;">
                    {st.session_state.ai_result['analysis']}
                </p>
                <div class="advice-tag">
                    <b>暖心贴士:</b><br>{st.session_state.ai_result['advice']}
                </div>
                <div style="margin-top:25px;">
                    <small style="opacity:0.6;">情绪能量波动</small>
                    <div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:10px; margin-top:8px; overflow:hidden;">
                        <div style="width:{st.session_state.mood_score*100}%; height:100%; background:{main_color}; box-shadow:0 0 15px {main_color}; transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 重新同步环境数据"):
            sync_environment()
            st.rerun()

elif st.session_state.current_page == "stats":
    st.title("📈 情感趋势档案")
    if st.button("⬅️ 返回监测控制台"):
        st.session_state.current_page = "main"
        st.rerun()
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        st.dataframe(df, use_container_width=True)
        
        # 简单的线性趋势
        mood_history = [x['score'] for x in st.session_state.chat_log]
        st.line_chart(mood_history)
    else:
        st.info("尚无记录，请在首页通过手势触发第一次分析。")
