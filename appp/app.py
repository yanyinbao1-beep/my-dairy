import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 全局样式：全年龄手写涂鸦风 ---
st.markdown("""
    <style>
    .stApp {
        background-color: #fdfaf5;
        background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png");
    }
    
    /* 结果展示卡片 */
    .result-card {
        background-color: rgba(255, 255, 255, 0.9);
        border: 2px dashed #6c757d;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 10px 10px 0px #eee;
    }

    .mood-icon-big {
        font-size: 120px;
        display: block;
        margin-bottom: 20px;
        animation: float 3s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-15px); }
    }

    /* 自定义按钮 */
    .stButton>button {
        border-radius: 12px;
        padding: 10px 25px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 逻辑初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "write"  # write, result, stats
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

try:
    client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")
except:
    st.error("🔑 请配置 API Key")

# --- 3. 页面导航逻辑 ---

# 页面 A：录入中心 (主页)
if st.session_state.current_page == "write":
    st.markdown("<h1 style='text-align:center;'>🖋️ 墨痕日记</h1>", unsafe_allow_html=True)
    st.write("---")
    
    # 居中布局
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        diary_input = st.text_area("今天的心情碎片...", placeholder="写下此刻的想法...", height=300, label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ 转换并存入", use_container_width=True):
                if diary_input:
                    with st.spinner("正在捕捉情绪..."):
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
                                "score": s,
                                "mood": res["mood"],
                                "advice": res["advice"],
                                "icon": icon,
                                "content": diary_input
                            }
                            st.session_state.diary_entries.insert(0, analysis)
                            st.session_state.last_analysis = analysis
                            st.session_state.current_page = "result" # 跳转到结果页
                            st.rerun()
                        except Exception as e:
                            st.error(f"分析失败: {e}")
        
        with col2:
            if st.button("📈 查看情绪波动", use_container_width=True):
                st.session_state.current_page = "stats"
                st.rerun()

# 页面 B：转换结果页 (提交后的变身效果)
elif st.session_state.current_page == "result":
    res = st.session_state.last_analysis
    st.markdown("<h2 style='text-align:center;'>✨ 情绪转换成功</h2>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(f"""
        <div class="result-card">
            <span class="mood-icon-big">{res['icon']}</span>
            <h3>当前状态：{res['mood']}</h3>
            <p style='color:#666; font-style:italic;'>“{res['advice']}”</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("↩️ 返回录入中心", use_container_width=True):
            st.session_state.current_page = "write"
            st.rerun()

# 页面 C：情绪波动监控页 (数据看板)
elif st.session_state.current_page == "stats":
    st.markdown("<h2 style='text-align:center;'>📊 情绪波动实时监测</h2>", unsafe_allow_html=True)
    
    if st.session_state.diary_entries:
        df = pd.DataFrame(st.session_state.diary_entries)
        
        # 情绪折线图
        st.write("### 📈 趋势曲线")
        chart_df = df.iloc[::-1] # 时间正序
        st.line_chart(chart_df.set_index("short_date")["score"])
        
        

        # 历史明细
        st.write("### 📜 历史存根")
        st.dataframe(df[["date", "mood", "content"]], use_container_width=True)
        
        if st.button("🗑️ 清空所有记录"):
            st.session_state.diary_entries = []
            st.rerun()
    else:
        st.info("目前还没有监测到数据，快去写第一篇日记吧！")
        
    if st.button("⬅️ 返回主页", use_container_width=True):
        st.session_state.current_page = "write"
        st.rerun()

# --- 底部装饰 ---
st.markdown("---")
st.caption("<center>每个瞬间都值得被记录</center>", unsafe_allow_html=True)
