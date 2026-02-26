import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉风格：全年龄段手绘涂鸦 ---
st.markdown("""
    <style>
    .stApp {
        background-color: #fdfaf5;
        background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png");
    }

    /* 左侧录入/结果盒子 */
    .input-card {
        background-color: rgba(255, 255, 255, 0.9);
        border: 2px solid #6c757d;
        border-radius: 15px;
        padding: 30px;
        min-height: 400px;
        box-shadow: 5px 5px 0px #e9ecef;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    /* 右侧监控灰格子 */
    .monitor-panel {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 15px;
        padding: 20px;
        min-height: 500px;
        background-image: 
            linear-gradient(rgba(200,200,200,0.2) 1px, transparent 1px),
            linear-gradient(90deg, rgba(200,200,200,0.2) 1px, transparent 1px);
        background-size: 20px 20px;
    }

    .mood-icon-main {
        font-size: 150px;
        margin: 20px 0;
        animation: bounce 2s infinite;
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "page_state" not in st.session_state:
    st.session_state.page_state = "input" # input or result

try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("🔑 请配置 API Key")

# --- 3. 页面布局 ---
st.markdown("<h1 style='text-align:center; color:#4a4a4a;'>📓 墨痕 AI 心情转换站</h1>", unsafe_allow_html=True)

col_left, col_right = st.columns([1.1, 0.9], gap="large")

# --- 左侧：动态录入中心 ---
with col_left:
    st.markdown("### 🖋️ 录入中心")
    
    # 状态 A：输入模式
    if st.session_state.page_state == "input":
        diary_input = st.text_area("", placeholder="写下此刻的想法，点击下方按钮转换...", height=350, key="input_box", label_visibility="collapsed")
        
        if st.button("✨ 转换心情并存入", use_container_width=True):
            if diary_input:
                with st.spinner("正在捕捉情绪分子..."):
                    try:
                        prompt = "分析情绪分数(0-1)及建议，返回JSON: {'score':float, 'mood':str, 'advice':str}"
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": diary_input}],
                            response_format={'type': 'json_object'}
                        )
                        res = json.loads(response.choices[0].message.content)
                        
                        s = res["score"]
                        icon = "🌞" if s>0.8 else "🌈" if s>0.6 else "☁️" if s>0.4 else "🌧️" if s>0.2 else "⛈️"
                        
                        new_entry = {
                            "date": datetime.now().strftime("%H:%M"),
                            "score": s,
                            "mood": res["mood"],
                            "advice": res["advice"],
                            "icon": icon,
                            "content": diary_input
                        }
                        st.session_state.diary_entries.insert(0, new_entry)
                        st.session_state.page_state = "result" # 切换到结果显示
                        st.rerun()
                    except Exception as e:
                        st.error(f"转换失败: {e}")

    # 状态 B：展示模式（提交后文字清空，显示表情）
    else:
        latest = st.session_state.diary_entries[0]
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="mood-icon-main">{latest["icon"]}</div>', unsafe_allow_html=True)
        st.markdown(f"## **{latest['mood']}**")
        st.write(f"“{latest['advice']}”")
        
        if st.button("↩️ 回到录入中心", use_container_width=True):
            st.session_state.page_state = "input"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 右侧：实时数据监控 ---
with col_right:
    st.markdown("### 📡 数据监控面板")
    st.markdown('<div class="monitor-panel">', unsafe_allow_html=True)
    
    if st.session_state.diary_entries:
        st.write("📈 **情绪波动实时监测**")
        df = pd.DataFrame(st.session_state.diary_entries)
        # 反转数据让折线图从左往右生长时间线
        chart_df = df.iloc[::-1]
        st.line_chart(chart_df.set_index("date")["score"])
        
        

        with st.expander("📜 历史记忆存根"):
            st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
            if st.button("🗑️ 清空所有记忆"):
                st.session_state.diary_entries = []
                st.rerun()
    else:
        st.write("📡 **传感器静默中...**")
        st.caption("请在左侧录入文字以激活监控。")
        
        

    st.markdown('</div>', unsafe_allow_html=True)
