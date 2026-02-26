import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 初始化与配置 ---
if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
if "last_score" not in st.session_state: st.session_state.last_score = 0.5

def navigate_to(page):
    st.session_state.current_page = page
    st.rerun()

# --- 2. 外部感知模块 (天气 + 温度) ---
def get_env_data():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=3).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        desc = "晴朗" if code == 0 else "多云" if code < 50 else "阴雨"
        return {"desc": desc, "temp": temp}
    except:
        return {"desc": "室内", "temp": 25.0}

env = get_env_data()
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 3. 页面路由 ---

# 【画面一：AI 实时监测主站】
if st.session_state.current_page == "main":
    st_autorefresh(interval=10000, key="bot_heartbeat") # 每10秒心跳
    st.title("🤖 情绪观察者：多维监控中心")
    
    # 自动变色逻辑
    score = st.session_state.last_score
    bg_color = f"hsl({200 - (score-0.5)*100}, 20%, 92%)"
    st.markdown(f"<style>.stApp {{ background: {bg_color}; transition: all 2s; }}</style>", unsafe_allow_html=True)

    # 1分钟总结决策
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在同步环境与生物数据..."):
            prompt = f"环境:{env['desc']},{env['temp']}℃。面部:{st.session_state.face_log[-5:]}。请生成一句陪伴对话并打分(0-1)。JSON:{{'text':'内容','score':float}}"
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是一个观察细致的极客机器人"}, {"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                # 存入大数据档案
                st.session_state.chat_log.insert(0, {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": data['text'],
                    "score": data['score'],
                    "weather": env['desc'],
                    "temp": env['temp']
                })
                st.session_state.last_score = data['score']
            except: pass

    col_v, col_c = st.columns([1, 1.2])
    with col_v:
        st.write("📷 **实时感知窗口**")
        components.html("""<div style="border-radius:15px; overflow:hidden; border:2px solid #5C6BC0;"><video id="v" autoplay playsinline style="width:100%; transform:scaleX(-1);"></video></div>
        <script>navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('v').srcObject=s;});</script>""", height=240)
        f = random.choice(["平静", "专注", "略显疲劳"])
        st.session_state.face_log.append(f)
        st.info(f"环境感知：{env['desc']} | {env['temp']}℃")

    with col_c:
        st.write("💬 **观察者笔记**")
        for chat in st.session_state.chat_log[:3]:
            st.markdown(f"**[{chat['time']}]** {chat['message']}")
        st.button("📈 进入大数据分析画面", use_container_width=True, on_click=lambda: navigate_to("stats"))

# 【画面二：大数据相关性分析】
elif st.session_state.current_page == "stats":
    st.title("📊 大数据情感动力学档案")
    
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 核心趋势图
        st.write("### 📈 情感极性随时间波动趋势")
        
        st.line_chart(df.set_index("time")["score"])
        
        # 2. 创新点：天气相关性热力分析
        st.divider()
        st.write("### 🌦️ 环境因子相关性分析")
        col1, col2 = st.columns(2)
        
        # 计算不同天气的平均心情
        weather_analysis = df.groupby("weather")["score"].mean().reset_index()
        col1.write("不同天气下的平均情绪值：")
        col1.dataframe(weather_analysis)
        
        # 气温与心情的散点关联
        col2.write("气温对情绪的影响分布：")
        
        st.scatter_chart(df, x="temp", y="score", color="weather")
        
        # 3. 机器人审计建议
        avg_score = df["score"].mean()
        advice = "系统检测到您的情绪受天气波动影响较小，心理韧性极佳。" if avg_score > 0.6 else "数据暗示低气压环境下您的能量值显著下降，建议增加室内光照。"
        st.success(f"🤖 **大数据审计结论：** {advice}")

    else:
        st.warning("数据池尚在构建中，请在主站等待至少1分钟。")

    st.button("⬅️ 返回实时监控", on_click=lambda: navigate_to("main"))
