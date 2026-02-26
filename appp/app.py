import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import requests
import pandas as pd
from datetime import datetime
import random
from streamlit_autorefresh import st_autorefresh

# --- 1. 页面配置与初始化 ---
st.set_page_config(page_title="多维情感监测终端", layout="wide")

if "current_page" not in st.session_state: st.session_state.current_page = "main"
if "face_log" not in st.session_state: st.session_state.face_log = []
if "chat_log" not in st.session_state: st.session_state.chat_log = []
if "start_time" not in st.session_state: st.session_state.start_time = datetime.now()
# 初始心情状态设为中性
if "last_metrics" not in st.session_state: 
    st.session_state.last_metrics = {"happiness": 0.5, "energy": 0.5, "stress": 0.2}

def navigate_to(page):
    st.session_state.current_page = page
    st.rerun()

# --- 2. 外部环境感知 ---
def get_env_data():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
        res = requests.get(url, timeout=3).json()
        return {"desc": "晴朗" if res['current_weather']['weathercode']==0 else "阴雨", "temp": res['current_weather']['temperature']}
    except:
        return {"desc": "室内", "temp": 25.0}

env = get_env_data()
client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 3. 动态视觉反馈 (基于多维指标) ---
m = st.session_state.last_metrics
# 背景色根据“压力”和“愉悦度”混合：压力高偏紫/灰，愉悦高偏黄/蓝
bg_color = f"hsl({200 - (m['happiness']-0.5)*100}, {20 + m['stress']*30}%, {90 - m['stress']*10}%)"
st.markdown(f"<style>.stApp {{ background: {bg_color}; transition: all 3s; }}</style>", unsafe_allow_html=True)

# --- 4. 画面路由 ---

if st.session_state.current_page == "main":
    st_autorefresh(interval=10000, key="bot_heartbeat")
    st.title("🤖 深度情感行为生成终端")
    
    # 60秒决策周期
    elapsed = (datetime.now() - st.session_state.start_time).seconds
    if elapsed >= 60:
        st.session_state.start_time = datetime.now()
        with st.spinner("🔍 正在进行多维情感建模..."):
            prompt = f"""
            环境:{env['desc']}。近期观测:{st.session_state.face_log[-6:]}。
            请作为深度心理观察机器人，分析用户的具体情绪。
            要求返回JSON，包含：
            1. text: 一句具体的、像人类一样观察入微的谈话。
            2. happiness: 愉悦度(0.0-1.0)
            3. energy: 能量值(0.0-1.0)
            4. stress: 压力值(0.0-1.0)
            5. label: 一个具体的情绪标签（如：平静的倦怠、隐秘的喜悦、专注的焦虑）。
            """
            try:
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是一个能读懂人类灵魂微表情的机器人"}, {"role": "user", "content": prompt}],
                    response_format={'type': 'json_object'}
                )
                data = json.loads(resp.choices[0].message.content)
                st.session_state.last_metrics = data
                st.session_state.chat_log.insert(0, {
                    "time": datetime.now().strftime("%H:%M"),
                    "message": data['text'],
                    "label": data['label'],
                    **data
                })
            except: pass

    # 界面布局
    col_v, col_c = st.columns([1, 1.2])
    with col_v:
        st.subheader("📸 实时生物轨迹")
        components.html("""<div style="border-radius:15px; overflow:hidden; border:2px solid #5C6BC0; background:#000;"><video id="v" autoplay playsinline style="width:100%; transform:scaleX(-1);"></video></div>
        <script>navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('v').srcObject=s;});</script>""", height=240)
        
        # 记录更具体的模拟特征
        f = random.choice(["眼睑轻微下垂", "视线在屏幕快速移动", "嘴角肌肉紧绷", "呼吸频率平稳"])
        st.session_state.face_log.append(f)
        st.write(f"🧬 **捕获特征：** {f}")
        
        # 显示当前具体标签
        current_label = st.session_state.chat_log[0]['label'] if st.session_state.chat_log else "初始化中"
        st.metric("核心情绪标签", current_label)

    with col_c:
        st.subheader("💬 主动行为生成日志")
        for chat in st.session_state.chat_log[:3]:
            st.markdown(f"**[{chat['time']}] {chat['label']}**")
            st.info(chat['message'])
        
        if st.button("📊 查看多维大数据档案", use_container_width=True):
            navigate_to("stats")

elif st.session_state.current_page == "stats":
    st.title("📊 多维情感大数据看板")
    if st.session_state.chat_log:
        df = pd.DataFrame(st.session_state.chat_log).iloc[::-1]
        
        # 1. 多维对比图
        st.write("### 📉 情绪多维波动图 (愉悦度 vs 能量 vs 压力)")
        st.line_chart(df.set_index("time")[["happiness", "energy", "stress"]])
        
        # 2. 情感空间分布
        st.divider()
        st.write("### 🌌 情感空间分布 (愉悦度 x 压力值)")
        st.scatter_chart(df, x="happiness", y="stress", color="label", size="energy")
        
        # 3. 数据审计
        st.write("### 📄 决策细节审计")
        st.dataframe(df[["time", "label", "message", "weather", "temp"]], use_container_width=True)
        
        st.download_button("📥 导出深度报告", df.to_csv().encode('utf-8-sig'), "emo_pro_report.csv", "text/csv", use_container_width=True)
    else:
        st.warning("暂无足够样本。")
    
    st.button("⬅️ 返回主站", on_click=lambda: navigate_to("main"))
