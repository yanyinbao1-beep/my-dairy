import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 极简美学：全屏横格背景，删除书本 ---
st.markdown("""
    <style>
    /* 全局背景：复古横格纸感 */
    .stApp {
        background-color: #fcf8f3;
        background-image: linear-gradient(#e1e1e1 1px, transparent 1px);
        background-size: 100% 2.5rem; /* 格纹高度 */
    }

    /* 文本框：完全透明，字写在格线上 */
    .stTextArea textarea {
        background: transparent !important;
        border: none !important;
        color: #2c3e50 !important;
        font-family: 'Kaiti', 'STKaiti', 'Microsoft YaHei', serif;
        font-size: 1.4rem !important;
        line-height: 2.5rem !important; /* 与格纹高度匹配 */
        padding-top: 0.1rem !important;
        box-shadow: none !important;
        height: 450px !important;
    }

    /* 聚焦时不显示蓝色边框 */
    .stTextArea textarea:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    /* 让折叠面板在视觉上更清晰 */
    .stExpander {
        background-color: rgba(255, 255, 255, 0.7);
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-top: 20px;
    }
    
    .main-title {
        font-family: 'Georgia', serif;
        color: #5d4037;
        background: #fcf8f3;
        display: inline-block;
        padding-right: 30px;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心配置与初始化 ---
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.info("💡 请在 Streamlit Secrets 中配置 api_key 以启用 AI 分析。")

if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""

# --- 3. 写作区域 ---
st.markdown('<h1 class="main-title">🖋️ 墨痕</h1>', unsafe_allow_html=True)

# 纯净的格纹输入区
diary_text = st.text_area(
    "", 
    value=st.session_state.current_text,
    placeholder="在此起笔...",
    key="diary_editor",
    label_visibility="collapsed"
)

# 保存按钮
col_btn_l, col_btn_m, col_btn_r = st.columns([1, 1, 1])
with col_btn_m:
    submit_btn = st.button("✨ 存入记忆", use_container_width=True)

# --- 4. 逻辑处理 ---
if submit_btn and diary_text:
    with st.spinner("AI 正在感知情绪..."):
        try:
            prompt = "分析日记情绪，返回JSON: {'score':0-1, 'mood':'词', 'advice':'建议'}"
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": diary_text}],
                response_format={'type': 'json_object'}
            )
            res = json.loads(response.choices[0].message.content)
            
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "content": diary_text,
                "score": res["score"],
                "mood": res["mood"],
                "advice": res["advice"]
            }
            st.session_state.diary_entries.insert(0, entry)
            st.session_state.current_text = "" 
            st.rerun()
        except Exception as e:
            st.error(f"分析失败，但日记已尝试保存。错误: {e}")

# --- 5. 数据面板（全部放入折叠按钮中） ---
if st.session_state.diary_entries:
    st.markdown("---")
    
    # 这一行是折叠按钮，所有的图表和表格都在里面
    with st.expander("📊 点击展开：情绪分析与历史回溯"):
        latest = st.session_state.diary_entries[0]
        
        # 今日摘要
        st.subheader(f"今日心情：{latest['mood']}")
        st.info(f"AI 的建议：{latest['advice']}")
        
        # 情绪图表
        st.markdown("#### 📈 情绪趋势曲线")
        df = pd.DataFrame(st.session_state.diary_entries)
        df['date'] = pd.to_datetime(df['date'])
        st.line_chart(df.set_index("date")["score"])
        
        # 历史表格
        st.markdown("#### 📜 往期日记明细")
        st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
        
        # 清空按钮也藏在这里
        if st.button("🗑️ 清空所有记录"):
            st.session_state.diary_entries = []
            st.rerun()
