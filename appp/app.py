import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉重塑：可爱手帐涂鸦风格 ---
st.markdown("""
    <style>
    /* 全局背景：浅粉米色 + 可爱点阵手帐感 */
    .stApp {
        background-color: #fff9fb;
        background-image: radial-gradient(#ffcfdf 1px, transparent 1px);
        background-size: 25px 25px; /* 点阵背景 */
    }

    /* 输入框：像在手帐贴纸上写字 */
    .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 2px dashed #ffb6c1 !important; /* 粉色虚线边框 */
        border-radius: 15px !important;
        color: #5d4037 !important;
        font-family: 'Kaiti', 'STKaiti', cursive;
        font-size: 1.2rem !important;
        padding: 15px !important;
        box-shadow: 5px 5px 0px #ffe4e1 !important;
    }

    /* 左侧：灰色格子感的 AI 结果 */
    .analysis-box {
        background-color: #f8f9fa; /* 灰色调 */
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 20px;
        min-height: 250px;
        background-image: linear-gradient(90deg, #f1f1f1 1px, transparent 1px), 
                          linear-gradient(#f1f1f1 1px, transparent 1px);
        background-size: 20px 20px; /* 灰格子背景 */
    }

    /* 标题样式：涂鸦感 */
    .cute-title {
        color: #ff69b4;
        font-family: 'Arial', sans-serif;
        text-shadow: 2px 2px #fff;
        border-bottom: 3px double #ffb6c1;
        display: inline-block;
        margin-bottom: 20px;
    }

    /* 自定义按钮 */
    .stButton>button {
        background-color: #ffb6c1;
        color: white;
        border-radius: 20px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff69b4;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心配置与数据 ---
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.info("🎨 正在使用手帐模式，请确保已配置 API 密钥。")

if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""

# --- 3. 页面布局 ---
st.markdown('<h1 class="cute-title">✨ 我的手帐日记</h1>', unsafe_allow_html=True)

# 写作区
diary_text = st.text_area(
    "", 
    value=st.session_state.current_text,
    placeholder="今天发生了什么可爱的事呢... ✏️",
    key="diary_editor",
    height=250,
    label_visibility="collapsed"
)

# 保存按钮
if st.button("🧸 记录这一刻", use_container_width=True):
    if diary_text:
        with st.spinner("正在涂鸦心情..."):
            try:
                prompt = "分析情绪，返回JSON: {'score':0-1, 'mood':'可爱词', 'advice':'简短治愈建议'}"
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": diary_text}],
                    response_format={'type': 'json_object'}
                )
                res = json.loads(response.choices[0].message.content)
                entry = {
                    "date": datetime.now().strftime("%m-%d %H:%M"),
                    "content": diary_text,
                    "score": res["score"],
                    "mood": res["mood"],
                    "advice": res["advice"]
                }
                st.session_state.diary_entries.insert(0, entry)
                st.session_state.current_text = "" 
                st.rerun()
            except Exception as e:
                st.error(f"哎呀，笔断了: {e}")

# --- 4. 底部展示区：左灰格子，右折叠图表 ---
if st.session_state.diary_entries:
    st.markdown("---")
    latest = st.session_state.diary_entries[0]
    
    col_left, col_right = st.columns([1, 1], gap="medium")
    
    with col_left:
        # 左边：灰色格子背景的分析结果
        st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
        st.markdown(f"### 🏷️ 今日标签: **{latest['mood']}**")
        st.write(f"**心灵寄语：** \n\n {latest['advice']}")
        st.markdown(f"<small style='color:gray'>{latest['date']}</small>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_right:
        # 右边：折叠的历史数据与图表
        with st.expander("📊 点击查看成长足迹", expanded=False):
            st.markdown("##### 📈 情绪起伏")
            df = pd.DataFrame(st.session_state.diary_entries)
            st.line_chart(df.set_index("date")["score"])
            
            st.markdown("##### 📜 往期明细")
            st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
            
            if st.button("🗑️ 清空记录"):
                st.session_state.diary_entries = []
                st.rerun()
