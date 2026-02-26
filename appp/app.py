import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉风格：封面与涂鸦样式 ---
st.markdown("""
    <style>
    .stApp {
        background-color: #fdfaf5;
        background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png");
    }
    
    /* 封面样式 */
    .cover-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 80vh;
        text-align: center;
    }
    
    .cover-title {
        font-family: 'Comic Sans MS', 'Kaiti', cursive;
        font-size: 4rem;
        color: #5d4037;
        margin-bottom: 10px;
        text-shadow: 3px 3px 0px #fff;
    }

    .cover-subtitle {
        font-size: 1.5rem;
        color: #8d6e63;
        margin-bottom: 40px;
    }

    /* 浮动动画 */
    .floating-deco {
        font-size: 50px;
        animation: float 4s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-20px); }
    }

    /* 结果卡片 */
    .result-card {
        background-color: rgba(255, 255, 255, 0.9);
        border: 2px dashed #6c757d;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        box-shadow: 10px 10px 0px #eee;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "cover"  # 默认起始页为封面
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.warning("🔑 请在后台配置 API Key 以开启 AI 功能")

# --- 3. 页面路由 ---

# 页面 0：封面页
if st.session_state.current_page == "cover":
    st.markdown("""
        <div class="cover-container">
            <div class="floating-deco">✨ 📖 ✨</div>
            <h1 class="cover-title">墨痕 · 心语</h1>
            <p class="cover-subtitle">在这里，听见文字呼吸的声音</p>
        </div>
    """, unsafe_allow_html=True)
    
    
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("点击开启日记本", use_container_width=True):
            st.session_state.current_page = "write"
            st.rerun()

# 页面 A：录入中心
elif st.session_state.current_page == "write":
    st.markdown("<h2 style='text-align:center;'>🖋️ 记录此刻</h2>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 3, 1])
    with col_b:
        diary_input = st.text_area("", placeholder="今天的心情是什么样的？", height=300, label_visibility="collapsed")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✨ 存入并转换", use_container_width=True):
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
                            
                            analysis = {
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "short_date": datetime.now().strftime("%m-%d %H:%M"),
                                "score": s, "mood": res["mood"], "advice": res["advice"],
                                "icon": icon, "content": diary_input
                            }
                            st.session_state.diary_entries.insert(0, analysis)
                            st.session_state.last_analysis = analysis
                            st.session_state.current_page = "result"
                            st.rerun()
                        except Exception as e:
                            st.error(f"分析失败: {e}")
        with c2:
            if st.button("📈 数据档案库", use_container_width=True):
                st.session_state.current_page = "stats"
                st.rerun()

# 页面 B：展示结果页
elif st.session_state.current_page == "result":
    res = st.session_state.last_analysis
    st.markdown("<h2 style='text-align:center;'>✨ 转换结果</h2>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(f"""
        <div class="result-card">
            <div style='font-size:100px;'>{res['icon']}</div>
            <h3>{res['mood']}</h3>
            <p style='color:#666;'>“{res['advice']}”</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("↩️ 回到日记本", use_container_width=True):
            st.session_state.current_page = "write"
            st.rerun()

# 页面 C：情绪监测页
elif st.session_state.current_page == "stats":
    st.markdown("<h2 style='text-align:center;'>📊 情绪波动档案</h2>", unsafe_allow_html=True)
    
    if st.session_state.diary_entries:
        df = pd.DataFrame(st.session_state.diary_entries)
        st.line_chart(df.iloc[::-1].set_index("short_date")["score"])
        
        
        
        with st.expander("📜 展开历史明细"):
            st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
    else:
        st.info("档案库空空如也。")
        
    if st.button("⬅️ 返回主页", use_container_width=True):
        st.session_state.current_page = "write"
        st.rerun()
