import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 全局页面配置 ---
st.set_page_config(page_title="EMO-Robot Terminal", layout="wide")

# 初始化 Session State
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_score" not in st.session_state: st.session_state.last_score = 0.5

# --- 2. 外部感知工具 ---
def get_env_data():
    """获取实时天气与温度 (Open-Meteo)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=3).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        desc = "晴朗" if code == 0 else "多云" if code < 50 else "阴雨"
        return {"desc": desc, "temp": temp}
    except:
        return {"desc": "室内模式", "temp": 25.0}

# 实例化 API (请确保在 Streamlit Secrets 中配置了 api_key)
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
env = get_env_data()

# --- 3. 动态视觉系统 (根据心情变色) ---
score = st.session_state.last_score
# 颜色算法：分值高(暖黄/明亮)，分值低(冷灰/幽暗)
bg_color = f"hsl({200 - (score-0.5)*120}, 25%, {92 + (score-0.5)*10}%)"
st.markdown(f"""
    <style>
    .stApp {{ background: {bg_color}; transition: background 3s ease-in-out; }}
    .bot-bubble {{ 
        background: rgba(255,255,255,0.85); border-radius: 15px; 
        padding: 15px; margin-bottom: 10px; border-left: 5px solid #4A90E2;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }}
    .metric-card {{
        background: white; padding: 15px; border-radius: 10px; text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 页面路由逻辑 ---

# 【画面 A：实时监控主站】
if st.session_state.current_page == "main":
    # 开启心跳：每10秒刷新感知，不阻塞用户
    st_autorefresh(interval=10000, key="bot_heartbeat")
    
    st.title("🤖 情绪观察者：机器人感知终端")
    st.markdown(f"**当前环境感知：** {env['desc']} | {env['temp']}℃ | **行为同步周期：** 60s")

    # --- 自动化逻辑：每 60 秒生成行为 ---
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        # 提取最近的生物特征描述
        recent_feats = st.session_state.face_log[-6:] if st.session_state.face_log else ["平和"]
        
        with st.spinner("🤖 机器人正在整合多模态数据并生成行为..."):
            prompt = f"环境:{env['desc']},{env['temp']}℃。近期面部特征:{recent_feats}。请作为智能机器人，生成一句100字内的关怀对话并打分(0-1)。JSON:{{'text':'内容','score':float}}"
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是具备高度同理心的观察者机器人"}, {"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                # 存入结构化日志
                st.session_state.chat_log.insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": data['text'],
                    "score": data['score'],
                    "weather": env['desc'],
                    "temp": env['temp']
                })
                st.session_state.last_score = data['score']
            except Exception as e:
                st.error(f"感知同步失败: {e}")

    # --- 界面布局 ---
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("📸 实时生物感应")
        # 实时摄像头流组件
        components.html("""
            <div style="border-radius:15px; overflow:hidden; border:2px solid #4A90E2; background:#000;">
                <video id="webcam" autoplay playsinline style="width:100%; transform:scaleX(-1); display:block;"></video>
            </div>
            <script>
                navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('webcam').srcObject=s;});
            </script>
        """, height=250)
        
        # 模拟生物特征提取
        current_feat = random.choice(["视线聚焦", "轻微蹙眉", "面部肌肉放松", "略显疲态"])
        st.session_state.face_log.append(current_feat)
        st.info(f"🧬 生物特征捕捉：{current_feat}")
        st.progress(elapsed/60, text="距离下次主动行为生成")

    with col_right:
        st.subheader("💬 机器人决策日志")
        if not st.session_state.chat_log:
            st.write("系统正在初始化感知，请保持自然状态...")
        for chat in st.session_state.chat_log[:3]:
            st.markdown(f"""<div class="bot-bubble"><small style="color:#666;">{chat['time']} - 观察决策：</small><br>{chat['message']}</div>""", unsafe_allow_html=True)
        
        st.divider()
        if st.button("📊 进入大数据分析档案库", use_container_width=True):
            st.session_state.current_page = "stats"
            st.rerun()

# 【画面 B：大数据分析档案库】
elif st.session_state.current_page == "stats":
    st.title("📊 大数据情感动力学档案")
    st.write("系统根据分钟级主动行为生成记录，构建的情感关联分析模型。")

    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1] # 按时间正序排列
        
        # 1. 情绪波动图
        st.subheader("📈 情感极性波动曲线")
        
        st.line_chart(df.set_index("time")["score"])
        
        # 2. 相关性分析
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("🌦️ **环境因子：天气与情绪关联**")
            weather_avg = df.groupby("weather")["score"].mean()
            st.bar_chart(weather_avg)
        with c2:
            st.write("🌡️ **气温因子：热度影响分布**")
            
            st.scatter_chart(df, x="temp", y="score", color="weather")

        # 3. 审计日志与导出
        st.divider()
        st.write("### 📄 决策审计记录")
        st.dataframe(df[["time", "message", "score", "weather", "temp"]], use_container_width=True)
        
        # 导出 Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 导出大数据情感报表 (CSV)",
            data=csv,
            file_name=f"emo_report_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.warning("数据池尚在构建中，请在主画面等待首个决策周期完成。")

    if st.button("⬅️ 返回实时监控终端", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()
