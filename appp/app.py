import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉重塑：儿童画蜡笔风格 ---
st.markdown("""
    <style>
    /* 全局背景：淡黄色纸张 + 蜡笔边缘感 */
    .stApp {
        background-color: #fffdf0;
        background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png"); /* 增加纸张质感 */
    }

    /* 标题：彩色蜡笔字效果 */
    .kids-title {
        font-family: 'Comic Sans MS', 'cursive', 'Kaiti';
        color: #ff6f61;
        text-shadow: 2px 2px #ffd700;
        font-size: 3rem;
        text-align: center;
        margin-bottom: 30px;
    }

    /* 左侧输入框：彩色粗边框便签 */
    .stTextArea textarea {
        background-color: #ffffff !important;
        border: 4px solid #4db8ff !important; /* 蜡笔蓝 */
        border-radius: 20px !important;
        font-size: 1.2rem !important;
        line-height: 1.6 !important;
        padding: 20px !important;
        box-shadow: 8px 8px 0px #bae1ff !important;
    }

    /* 右侧监控区：灰色小格子背景 */
    .monitor-box {
        background-color: #f0f0f0;
        border: 3px dashed #999;
        border-radius: 15px;
        padding: 20px;
        min-height: 400px;
        background-image: radial-gradient(#d0d0d0 1px, transparent 1px);
        background-size: 15px 15px; /* 监控感灰格子 */
    }

    /* 按钮：圆润的彩色块 */
    .stButton>button {
        background-color: #ffcc00 !important;
        color: #5d4037 !important;
        border-radius: 50px !important;
        border: 3px solid #ff9900 !important;
        font-weight: bold !important;
        height: 3em !important;
    }
    
    /* 标签装饰 */
    .badge {
        background-color: #ff6f61;
        color: white;
        padding: 5px 15px;
        border-radius: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心配置与初始化 ---
try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.info("🧸 欢迎来到童心日记！请记得在 Secret 填入咒语 (API Key)。")

if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_text" not in st.session_state:
    st.session_state.current_text = ""

# --- 3. 页面标题 ---
st.markdown('<h1 class="kids-title">🖍️ 涂鸦日记监控台</h1>', unsafe_allow_html=True)

# --- 4. 左右分栏布局 ---
col_input, col_monitor = st.columns([1, 1], gap="large")

with col_input:
    st.markdown("### ✏️ 写下你的秘密...")
    diary_text = st.text_area(
        "", 
        value=st.session_state.current_text,
        placeholder="今天吃了什么好吃的？或者有什么开心的事？",
        key="diary_editor",
        height=350,
        label_visibility="collapsed"
    )
    
    if st.button("🚀 砰！存进时光机", use_container_width=True):
        if diary_text:
            with st.spinner("正在捕捉你的心情小怪兽..."):
                try:
                    prompt = "分析情绪，返回JSON: {'score':0-1, 'mood':'超级可爱的词', 'advice':'建议'}"
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
                    st.error(f"哎呀，时光机没电了: {e}")

with col_monitor:
    st.markdown("### 📡 实时情绪监控")
    st.markdown('<div class="monitor-box">', unsafe_allow_html=True)
    
    if st.session_state.diary_entries:
        latest = st.session_state.diary_entries[0]
        
        # 实时心情显示
        st.markdown(f"**心情探测结果：** <span class='badge'>{latest['mood']}</span>", unsafe_allow_html=True)
        st.markdown(f"**心灵贴纸：** \n\n {latest['advice']}")
        
        st.divider()
        
        # 折叠图表区域
        with st.expander("📉 查看历史记录与图表"):
            st.markdown("##### 情绪起伏监控")
            df = pd.DataFrame(st.session_state.diary_entries)
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format="%m-%d %H:%M")
            st.line_chart(df.set_index("date")["score"])
            
            st.markdown("##### 历史明细")
            st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
            
            if st.button("🧹 打扫日记本 (清空)"):
                st.session_state.diary_entries = []
                st.rerun()
    else:
        st.write("还没有探测到任何心情，快去左边写点什么吧！🌈")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. 底部装饰 ---
st.markdown("<center style='color:#ccc; margin-top:50px;'>Made with ❤️ for Kids</center>", unsafe_allow_html=True)
