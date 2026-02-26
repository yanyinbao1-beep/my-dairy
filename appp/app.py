import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime
import time

# --- 1. 深度美化：CSS 样式注入 ---
# 为日记本和翻页效果注入自定义 CSS
st.markdown("""
    <style>
    /* 全局背景：柔和的浅米色，模拟舒适的阅读环境 */
    .stApp {
        background-color: #fcf8f3; 
        font-family: 'Times New Roman', serif;
    }
    
    /* 模拟日记本容器 */
    .diary-container {
        display: flex;
        perspective: 1500px; /* 3D 视角 */
        justify-content: center;
        margin-top: 20px;
    }

    /* 日记本单页样式 */
    .diary-page {
        background-color: #ffffff; /* 纯白纸张 */
        border: 1px solid #ddd;
        border-radius: 4px;
        box-shadow: 5px 5px 20px rgba(0,0,0,0.15); /* 更真实的阴影 */
        padding: 30px;
        width: 48%; /* 占据一半宽度 */
        min-height: 500px;
        margin: 10px;
        position: relative;
        transform-origin: left center; /* 翻页效果的轴心 */
        transition: transform 0.8s ease-in-out; /* 翻页动画 */
        font-size: 1.1em;
        line-height: 1.6;
        color: #333;
    }

    /* 纸张横线效果 */
    .diary-page::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: repeating-linear-gradient(to bottom, transparent, transparent 1.5em, #e0e0e0 1.5em, #e0e0e0 1.6em);
        background-size: 100% 1.6em;
        opacity: 0.7; /* 淡化横线 */
        pointer-events: none; /* 不影响点击 */
    }
    
    /* 左侧页的书脊 */
    .diary-page.left::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 8px; /* 书脊宽度 */
        height: 100%;
        background-color: #a0522d; /* 书脊颜色 */
        border-radius: 4px 0 0 4px;
    }

    /* 文本框样式，使其看起来像直接写在纸上 */
    .stTextArea > div > div > textarea {
        background: none !important; /* 移除默认背景 */
        border: none !important; /* 移除边框 */
        box-shadow: none !important; /* 移除阴影 */
        padding: 0;
        font-family: 'Times New Roman', serif;
        font-size: 1.1em;
        line-height: 1.6;
        color: #2c3e50; /* 深色文字 */
        resize: none; /* 禁止用户调整大小 */
    }
    
    /* 打字机效果动画 - AI回复 */
    .typing-effect {
        overflow: hidden; /* 隐藏超出部分 */
        white-space: pre-wrap; /* 允许换行 */
        font-family: 'Courier New', monospace; /* 模拟打印字体 */
        border-right: .05em solid #888; /* 光标 */
        animation: blink-caret .75s step-end infinite;
    }
    @keyframes blink-caret {
      from, to { border-color: transparent }
      50% { border-color: #888; }
    }
    
    /* 标题居中 */
    h1 {
        text-align: center;
        color: #6a4025; /* 深棕色标题 */
        font-family: 'Georgia', serif;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #a0522d; /* 按钮背景 */
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 1em;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #8b4513;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API 配置 ---
client = OpenAI(api_key="sk-16473a63348648bf92c6cdfd33457382", base_url="https://api.deepseek.com")

# --- 3. 初始化日记本存储 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_diary_content" not in st.session_state:
    st.session_state.current_diary_content = "" # 用于在翻页时清空文本框

# --- 4. 页面主体布局 ---
st.title("💖 心语 AI 电子日记")
st.caption("记录日常点滴，洞察情绪起伏，让 AI 成为你的专属倾听者。")

st.markdown('<div class="diary-container">', unsafe_allow_html=True) # 日记本容器

# --- 左侧：日记撰写页 ---
# 这一行必须存在！它负责把页面分成两栏
col_left, col_right = st.columns([1, 1], gap="large")
with col_left:
    # 使用 Markdown 创造一个带有点阵感的纸张区域
    st.markdown('<div class="diary-page left">', unsafe_allow_html=True)
    
    st.markdown("<h3 style='color: #8b4513; font-family: KaiTi;'>🖋️ 亲笔记录</h3>", unsafe_allow_html=True)
    
    # 这里的 key="diary_input" 非常重要
    # 如果依然看不见，请检查浏览器是否开启了某些强制深色模式的插件
    diary_content = st.text_area(
        "在此处输入你的日记内容...", 
        value=st.session_state.current_diary_content, 
        height=350, 
        key="diary_input",
        help="点击下方空白处开始写字"
    )
    
    # 放一个明显的按钮
    submit_btn = st.button("📖 记好了，翻页！", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- 右侧：AI 洞察与历史记录 ---
with st.empty(): # 同样使用 st.empty()
    st.markdown('<div class="diary-page right">', unsafe_allow_html=True)
    st.subheader("💡 AI 心灵回响")
    
    if st.session_state.diary_entries:
        latest = st.session_state.diary_entries[0]
        st.markdown(f"<p style='font-size:1.2em; font-weight:bold; color:#d64500;'>今日心情：{latest['mood']}</p>", unsafe_allow_html=True)
        st.progress(latest["score"])
        st.caption(f"心理能量值: {int(latest['score']*100)}%")
        
        st.markdown("<hr style='border-top: 1px dashed #ccc;'>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-weight:bold; color:#6a4025;'>AI 给予你的建议:</p>", unsafe_allow_html=True)
        
        # AI 建议的打字机效果
        advice_placeholder = st.empty()
        full_advice = latest['advice']
        typed_advice = ""
        for char in full_advice:
            typed_advice += char
            advice_placeholder.markdown(f'<div class="typing-effect">{typed_advice}</div>', unsafe_allow_html=True)
            time.sleep(0.02) # 调节打字速度
        
        st.markdown(f'<div class="typing-effect">{full_advice}</div>', unsafe_allow_html=True) # 最终显示完整文本
        
    else:
        st.info("写下你的第一篇日记，AI 将为你解读心灵。")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # 关闭日记本容器
# --- 5. 提交按钮逻辑 ---
if submit_btn and diary_content:
    with st.spinner("AI 正在研读你的心声，请稍候..."):
        SYSTEM_PROMPT = """
        你是一个富有同情心的日记分析师。请分析日记内容，返回 JSON 格式：
        {
          "score": 0.0到1.0 (0为极度负面，1为极度正面),
          "keywords": ["心情词", "事件词"],
          "advice": "一段充满理解、支持和启发性的建议",
          "mood_label": "心情总结词 (如：平静、焦虑、喜悦、沮丧)"
        }
        请确保分数和情绪标签与内容高度匹配。
        """
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": diary_content}],
                response_format={'type': 'json_object'}
            )
            res = json.loads(response.choices[0].message.content)
            
            new_entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "content": diary_content,
                "score": res["score"],
                "mood": res["mood_label"],
                "advice": res["advice"]
            }
            st.session_state.diary_entries.insert(0, new_entry) # 最新日记放在最前面
            st.session_state.current_diary_content = "" # 清空输入框，模拟翻页
            
            st.toast("日记已保存，AI 洞察已更新！✨", icon="📖")
            
            # 触发 Streamlit 特效
            if res["score"] < 0.3:
                st.snow()
            elif res["score"] > 0.8:
                st.balloons()
            
            # 强制 Streamlit 重新运行，以更新所有显示，包括清空的文本框
            st.rerun()
            
        except Exception as e:
            st.error(f"分析失败，请检查 API Key 或网络连接: {e}")
            # --- 6. 底部：历史足迹与情绪趋势图 (放入抽屉) ---
st.divider()

# 使用 expander 模拟“查看往期回忆”
with st.expander("📜 点击查看：往期情绪记忆与足迹"):
    if st.session_state.diary_entries:
        history_df = pd.DataFrame(st.session_state.diary_entries)
        
        col_chart, col_table = st.columns([1, 1])
        
        with col_chart:
            st.markdown("#### 📈 情绪起伏曲线")
            # 这里的日期需要转换成索引才能画图
            chart_df = history_df.copy()
            st.line_chart(chart_df.set_index("date")["score"])
            
        with col_table:
            st.markdown("#### 📖 最近日记摘录")
            st.dataframe(history_df[['date', 'mood', 'content']].head(10), use_container_width=True)
            
        if st.button("🗑️ 永久封存（清空记录）"):
            st.session_state.diary_entries = []
            st.session_state.current_diary_content = ""
            st.rerun()
    else:
        st.write("日记本还是空的，快去写下第一篇吧！")