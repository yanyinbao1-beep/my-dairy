import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json, requests, pandas as pd
from datetime import datetime
import time

# --- 1. 核心配置与状态初始化 ---
st.set_page_config(page_title="Emo-Bot Pro", layout="wide", initial_sidebar_state="collapsed")

# 必须初始化的状态变量
init_states = {
    "booted": False,
    "current_page": "main",
    "chat_log": [],  # 存储所有历史分析记录
    "env_data": {"city": "定位中", "temp": "20"},
    "mood_score": 0.5, # 0: 忧郁蓝, 1: 活力橙
    "last_ana_time": 0, # 用于实现每分钟自动分析
    "ai_result": {"label": "感知中", "analysis": "系统初始化...", "advice": "准备开启监测"}
}
for key, val in init_states.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 2. 动态主题引擎 (颜色随心情自动同步) ---
# 根据 mood_score (0.0~1.0) 计算 HSL 色相 (220 蓝 -> 40 橙)
hue = 220 - (st.session_state.mood_score * 180)
main_color = f"hsla({hue}, 75%, 60%, 1)"
bg_gradient = f"radial-gradient(circle at 50% 50%, hsla({hue}, 45%, 12%, 1) 0%, #0a1118 100%)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_gradient}; color: white; transition: background 2s ease; }}
    .glass-card {{
        background: rgba(255, 255, 255, 0.03); border: 1px solid {main_color}44;
        border-radius: 20px; padding: 25px; backdrop-filter: blur(12px);
        box-shadow: 0 10px 40px rgba(0,0,0,0.5); margin-bottom: 20px;
    }}
    .advice-tag {{
        background: {main_color}15; border-left: 4px solid {main_col} !important;
        padding: 15px; margin-top: 15px; border-radius: 8px; font-style: italic;
    }}
    /* 动态扫描封面 */
    #loader {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: #0a1118; display: flex; flex-direction: column;
        align-items: center; justify-content: center; z-index: 9999;
    }}
    .scanner-bar {{
        width: 300px; height: 2px; background: {main_color};
        box-shadow: 0 0 20px {main_color}; animation: scanMove 2.5s infinite ease-in-out;
    }}
    @keyframes scanMove {{ 0%, 100% {{ transform: translateY(-50px); }} 50% {{ transform: translateY(50px); }} }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 定位、天气与 AI 自动化逻辑 ---
def sync_env_data():
    """获取定位与天气，失败则兜底"""
    try:
        r = requests.get("https://ipapi.co/json/", timeout=2.5).json()
        city = r.get("city", "上海")
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={r.get('latitude',31)}&longitude={r.get('longitude',121)}&current_weather=true").json()
        st.session_state.env_data = {"city": city, "temp": str(w['current_weather']['temperature'])}
    except:
        st.session_state.env_data = {"city": "北京", "temp": "18"}

def perform_auto_ai_analysis():
    """核心：每隔 60 秒自动触发 AI 分析并记录"""
    current_time = time.time()
    if current_time - st.session_state.last_ana_time >= 60:
        if "api_key" not in st.secrets: return # 无 Key 则跳过
        client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
        try:
            prompt = f"城市：{st.session_state.env_data['city']}，气温：{st.session_state.env_data['temp']}°C。请作为暖心伴侣，根据此时的环境提供：1. 四字表情标签；2. 30字情绪画像；3. 一句结合天气的暖心关怀建议。JSON格式返回：{{'label':'','text':'','adv':'','score':0.0-1.0}}"
            r = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={'type':'json_object'})
            data = json.loads(r.choices[0].message.content)
            
            # 更新实时状态
            st.session_state.ai_result = {"label": data['label'], "analysis": data['text'], "advice": data['adv']}
            st.session_state.mood_score = data['score']
            st.session_state.last_ana_time = current_time
            
            # 记录历史数据（用于图表生成）
            st.session_state.chat_log.append({
                "时间": datetime.now().strftime("%H:%M:%S"),
                "情绪状态": data['label'],
                "AI 分析": data['text'],
                "气温": f"{st.session_state.env_data['temp']}°C",
                "心情得分": data['score']
            })
        except: pass

# --- 4. 动态启动封面 ---
if not st.session_state.booted:
    ph = st.empty()
    with ph.container():
        st.markdown(f'<div id="loader"><div class="scanner-bar"></div><h3 style="color:{main_color};margin-top:20px;letter-spacing:4px;">EMO-BOT INITIALIZING</h3></div>', unsafe_allow_html=True)
        sync_env_data()
        time.sleep(2.5)
    st.session_state.booted = True
    st.rerun()

# 每次渲染都尝试检查是否需要自动分析
perform_auto_ai_analysis()

# --- 5. 主界面路由渲染 ---
if st.session_state.current_page == "main":
    st.write(f"📍 {st.session_state.env_data['city']} | 🌡️ {st.session_state.env_data['temp']}°C")
    
    col_l, col_r = st.columns([1.3, 0.7])
    
    with col_l:
        st.subheader("📸 21-Node 实时监测 (比✌️跳转)")
        # 强制绘制节点与连线
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
                hands.setOptions({{maxNumHands:1, minDetectionConfidence:0.6}});
                hands.onResults((res)=>{{
                    ctx.clearRect(0,0,c.width,c.height);
                    if(res.multiHandLandmarks){{
                        for(const lm of res.multiHandLandmarks){{
                            drawConnectors(ctx, lm, HAND_CONNECTIONS, {{color:'#00FF00', lineWidth:2}});
                            drawLandmarks(ctx, lm, {{color:'#FF0000', radius:3}});
                            // ✌️ 手势跳转判定
                            if(lm[8].y < lm[6].y && lm[12].y < lm[10].y && lm[16].y > lm[14].y) {{
                                window.parent.document.querySelector('button[kind="primary"]').click();
                            }}
                        }}
                    }}
                }});
                new Camera(v,{{onFrame:async()=>{{c.width=v.videoWidth; c.height=v.videoHeight; await hands.send({{image:v}});}}}}).start();
            </script>
        """, height=440)
        
        # 隐藏但可被 JS 触发的按钮
        if st.button("📈 进入情绪趋势大屏", type="primary", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

    with col_r:
        st.subheader("🤖 每分钟自动诊断")
        st.markdown(f"""
            <div class="glass-card">
                <small style="opacity:0.6;">最后同步: {datetime.now().strftime("%H:%M:%S")}</small>
                <h2 style="color:{main_color}; margin:10px 0;">{st.session_state.ai_result['label']}</h2>
                <p style="font-size:1em; line-height:1.6;">{st.session_state.ai_result['analysis']}</p>
                <div class="advice-tag">
                    <b>💡 暖心关怀：</b><br>{st.session_state.ai_result['advice']}
                </div>
                <div style="margin-top:25px;">
                    <small>实时情绪能量 (分数: {st.session_state.mood_score})</small>
                    <div style="width:100%; height:6px; background:rgba(255,255,255,0.05); border-radius:10px; margin-top:8px;">
                        <div style="width:{st.session_state.mood_score*100}%; height:100%; background:{main_color}; box-shadow:0 0 10px {main_color}; transition: 2s;"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 手动刷新感官"):
            st.session_state.last_ana_time = 0 
            st.rerun()

# --- 6. 趋势图表与历史记录页面 ---
elif st.session_state.current_page == "stats":
    st.title("📈 情绪历史报告与趋势图表")
    if st.button("⬅️ 返回实况监测台"):
        st.session_state.current_page = "main"
        st.rerun()
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log)
        
        # 数据可视化：情绪趋势图表
        st.subheader("📊 心情波动曲线")
        # 准备图表数据
        chart_data = df[["时间", "心情得分"]].set_index("时间")
        st.line_chart(chart_data, color=main_color)
        
        # 历史明细记录
        st.subheader("📜 详细诊断记录")
        st.table(df.iloc[::-1]) # 倒序显示最新的
    else:
        st.info("系统尚在初始化，正在等待第一分钟的自动分析生成...")
