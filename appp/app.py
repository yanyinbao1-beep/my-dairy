import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉风格：全年龄手绘涂鸦 + 纸张质感 ---
st.markdown("""
    <style>
    /* 全局背景：纸张质感 + 随机涂鸦元素 */
    .stApp {
        background-color: #fdfaf5;
        background-image: 
            url("https://www.transparenttextures.com/patterns/paper-fibers.png"),
            url("https://www.transparenttextures.com/patterns/hand-made-paper.png");
        background-attachment: fixed;
    }

    /* 标题：手写感 */
    .main-title {
        font-family: 'Comic Sans MS', 'Kaiti', cursive;
        color: #4a4a4a;
        text-align: center;
        padding: 20px;
        border-bottom: 2px dashed #ccc;
        margin-bottom: 30px;
    }

    /* 左侧输入框：极简便签感 */
    .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 2px solid #6c757d !important;
        border-radius: 12px !important;
        font-size: 1.2rem !important;
        color: #333 !important;
        padding: 20px !important;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05) !important;
    }

    /* 右侧监控区：精密灰格子背景 */
    .monitor-panel {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 15px;
        padding: 25px;
        min-height: 450px;
        /* 经典的工程灰格子 */
        background-image: 
            linear-gradient(rgba(200,200,200,0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(200,200,200,0.3) 1px, transparent 1px);
        background-size: 20px 20px;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.02);
    }

    /* 按钮样式：中性且专业 */
    .stButton>button {
        background-color: #4a4a4a !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 20px !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2c2c2c !important;
        transform: translateY(-2px);
    }

    /* 心情标签 */
    .mood-tag {
        background: #e9ecef;
        color: #495057;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #ced4da;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.info("👋 欢迎！请在后台配置 API Key 以开启 AI 情绪监测。")

if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""

# --- 3. 页面内容 ---
st.markdown('<h1 class="main-title">📓 墨痕 AI 随笔监控</h1>', unsafe_allow_html=True)

# 布局：左(输入) 右(监控)
col_left, col_right = st.columns([1.2, 0.8], gap="large")

with col_left:
    st.markdown("### 🖋️ 此时此刻")
    content = st.text_area(
        "",
        value=st.session_state.current_text,
        placeholder="在这里输入你的想法、心情或故事...",
        height=400,
        key="editor",
        label_visibility="collapsed"
    )
    
    if st.button("确认存入记忆库", use_container_width=True):
        if content:
            with st.spinner("AI 正在解析数据流..."):
                try:
                    prompt = "分析情绪，返回JSON: {'score':0-1, 'mood':'准确的情绪词', 'advice':'简短深刻的共情建议'}"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": content}],
                        response_format={'type': 'json_object'}
                    )
                    res = json.loads(response.choices[0].message.content)
                    entry = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "content": content,
                        "score": res["score"],
                        "mood": res["mood"],
                        "advice": res["advice"]
                    }
                    st.session_state.diary_entries.insert(0, entry)
                    st.session_state.current_text = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"连接失败: {e}")

with col_right:
    st.markdown("### 📊 实时监控看板")
    st.markdown('<div class="monitor-panel">', unsafe_allow_html=True)
    
    if st.session_state.diary_entries:
        latest = st.session_state.diary_entries[0]
        
        # 核心指标
        st.write(f"📅 **时间:** {latest['date']}")
        st.markdown(f"🎭 **当前状态:** <span class='mood-tag'>{latest['mood']}</span>", unsafe_allow_html=True)
        st.write(f"💡 **AI 建议:** {latest['advice']}")
        
        st.divider()
        
        # 压缩件：折叠图表
        with st.expander("📈 历史波动图表", expanded=False):
            df = pd.DataFrame(st.session_state.diary_entries)
            df['date'] = pd.to_datetime(df['date'])
            # 情绪折线图
            st.line_chart(df.set_index("date")["score"])
            # 历史数据表
            st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
            
            if st.button("清空所有数据"):
                st.session_state.diary_entries = []
                st.rerun()
    else:
        st.info("等待数据输入中... 请在左侧完成首次记录。")
    
    st.markdown('</div>', unsafe_allow_html=True)
