import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉风格：全年龄段手绘涂鸦背景 ---
st.markdown("""
    <style>
    .stApp {
        background-color: #fdfaf5;
        background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png");
        background-attachment: fixed;
    }

    .main-title {
        font-family: 'Comic Sans MS', 'Kaiti', cursive;
        color: #4a4a4a;
        text-align: center;
        border-bottom: 2px dashed #ccc;
        margin-bottom: 20px;
    }

    /* 左侧输入框 */
    .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 2px solid #6c757d !important;
        border-radius: 12px !important;
        font-size: 1.1rem !important;
    }

    /* 右侧监控灰格子 */
    .monitor-panel {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 15px;
        padding: 30px;
        min-height: 550px;
        background-image: 
            linear-gradient(rgba(200,200,200,0.2) 1px, transparent 1px),
            linear-gradient(90deg, rgba(200,200,200,0.2) 1px, transparent 1px);
        background-size: 20px 20px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }

    .mood-icon-large {
        font-size: 120px;
        filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.1));
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "monitor_state" not in st.session_state:
    st.session_state.monitor_state = "idle" # idle, loading, result

try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("🔑 请在后台配置 API Key")

# --- 3. 页面布局 ---
st.markdown('<h1 class="main-title">📓 墨痕 AI 情绪监控终端</h1>', unsafe_allow_html=True)

col_left, col_right = st.columns([1.1, 0.9], gap="large")

# --- 左侧：输入区域 + 历史图表 ---
with col_left:
    st.markdown("### 🖋️ 录入中心")
    diary_input = st.text_area("", placeholder="描述你此刻的感受...", height=250, key="main_input", label_visibility="collapsed")
    
    if st.button("🚀 提交分析", use_container_width=True):
        if diary_input:
            st.session_state.monitor_state = "loading"
            # 模拟扫描延迟感
            try:
                prompt = "分析情绪分数(0-1)及建议，返回JSON: {'score':float, 'mood':str, 'advice':str}"
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": diary_input}],
                    response_format={'type': 'json_object'}
                )
                res = json.loads(response.choices[0].message.content)
                
                # 图标映射
                s = res["score"]
                icon = "🌞" if s>0.8 else "🌈" if s>0.6 else "☁️" if s>0.4 else "🌧️" if s>0.2 else "⛈️"
                
                new_entry = {
                    "date": datetime.now().strftime("%H:%M"),
                    "full_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "score": s,
                    "mood": res["mood"],
                    "advice": res["advice"],
                    "icon": icon,
                    "content": diary_input
                }
                st.session_state.diary_entries.insert(0, new_entry)
                st.session_state.monitor_state = "result"
                st.rerun()
            except Exception as e:
                st.error(f"分析中断: {e}")
                st.session_state.monitor_state = "idle"

    # --- 左侧下方：历史图表压缩件 ---
    if st.session_state.diary_entries:
        st.markdown("---")
        st.markdown("### 📈 情绪追踪曲线")
        df = pd.DataFrame(st.session_state.diary_entries)
        # 仅显示最近10条趋势
        chart_df = df.iloc[::-1].tail(10) 
        st.line_chart(chart_df.set_index("date")["score"])
        
        with st.expander("📜 历史存根"):
            st.dataframe(df[["full_date", "mood", "content"]], use_container_width=True)
            if st.button("清空数据库"):
                st.session_state.diary_entries = []
                st.rerun()

# --- 右侧：实时监控动态显示 ---
with col_right:
    st.markdown("### 📡 实时监控看板")
    st.markdown('<div class="monitor-panel">', unsafe_allow_html=True)
    
    if st.session_state.monitor_state == "loading":
        st.write("### 🔍 正在扫描...")
        
        st.write("正在捕获脑电波频率...")
        
    elif st.session_state.monitor_state == "result" and st.session_state.diary_entries:
        latest = st.session_state.diary_entries[0]
        st.markdown(f'<div class="mood-icon-large">{latest["icon"]}</div>', unsafe_allow_html=True)
        st.markdown(f"## **{latest['mood']}**")
        st.write(f"💡 {latest['advice']}")
        
        if st.button("🧹 重置看板"):
            st.session_state.monitor_state = "idle"
            st.rerun()
            
    else:
        st.write("### 📡 监控静默中")
        
        st.caption("等待左侧数据传输...")
        
    st.markdown('</div>', unsafe_allow_html=True)
