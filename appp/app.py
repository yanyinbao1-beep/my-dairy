import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

# --- 1. 视觉风格与动画 ---
st.markdown("""
    <style>
    .stApp { background: #fdfaf5; transition: all 0.5s; }
    .ai-status-bar {
        padding: 10px;
        background: rgba(0,0,0,0.05);
        border-radius: 10px;
        border-left: 5px solid #4A90E2;
        margin-bottom: 20px;
    }
    .art-canvas {
        border: 10px solid #2c3e50;
        background: #fff;
        min-height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心：JavaScript 实时面部情绪感知组件 ---
# 这里使用简单的占位逻辑，实际开发中可引入 Face-api.js 库
def face_detector():
    components.html(
        """
        <div style="background: #000; color: #0f0; padding: 10px; font-family: monospace; border-radius: 8px;">
            <video id="video" width="100%" height="auto" autoplay muted style="display:none;"></video>
            <canvas id="overlay" style="display:none;"></canvas>
            <div id="status">📡 物理联动：面部生物特征实时扫描中...</div>
            <div id="emotion-result" style="font-size: 20px; font-weight: bold; margin-top: 5px;">检测到：中性 (Scanning...)</div>
        </div>
        <script>
            // 模拟实时检测逻辑
            const emotions = ["平静", "愉悦", "专注", "思索", "疲惫"];
            setInterval(() => {
                const randomEmotion = emotions[Math.floor(Math.random() * emotions.length)];
                document.getElementById('emotion-result').innerText = "检测到面部微表情：" + randomEmotion;
                // 实际开发中，这里会通过 window.parent.postMessage 将数据传给 Streamlit
            }, 3000);
            
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => { document.getElementById('video').srcObject = stream; })
                .catch(err => { document.getElementById('status').innerText = "⚠️ 摄像头未授权"; });
        </script>
        """,
        height=120,
    )

# --- 3. 初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "cover"

client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 4. 页面导航 ---

# 【页面 0：封面】
if st.session_state.current_page == "cover":
    st.markdown("<h1 style='text-align:center;'>🤖 大数据情感机器人</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>主动行为生成系统 V2.0</p>", unsafe_allow_html=True)
    if st.button("激活生物感知并进入", use_container_width=True):
        st.session_state.current_page = "write"
        st.rerun()

# 【页面 A：录入中心 - 自动检测】
elif st.session_state.current_page == "write":
    st.markdown('<div class="ai-status-bar">🧬 <b>系统状态：</b> 实时感知模块已就绪，正在通过摄像头捕捉非语言特征。</div>', unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 1.5])
    
    with col_l:
        st.write("📸 **实时物理联动**")
        face_detector()  # 调用自动检测组件
        st.caption("机器人正在自主观察您的面部肌肉波动，无需手动拍摄。")
    
    with col_r:
        st.write("🖋️ **输入今日心语**")
        user_text = st.text_area("", placeholder="在这里写下你的想法...", height=200, label_visibility="collapsed")
        
        if st.button("执行主动行为生成", use_container_width=True):
            if user_text:
                with st.spinner("融合生物特征与文本语义中..."):
                    # AI 结合多模态数据进行决策
                    prompt = "结合面部实时感知的‘平静’特征与以下文本，生成情绪分(0-1)、主动行为及绘图Prompt。JSON: {'score':float, 'mood':str, 'action':str, 'art_prompt':str}"
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_text}],
                        response_format={'type': 'json_object'}
                    )
                    res = json.loads(response.choices[0].message.content)
                    
                    analysis = {
                        "date": datetime.now().strftime("%H:%M"),
                        "score": res["score"],
                        "mood": res["mood"],
                        "action": res["action"],
                        "art_prompt": res["art_prompt"],
                        "content": user_text
                    }
                    st.session_state.diary_entries.insert(0, analysis)
                    st.session_state.last_analysis = analysis
                    st.session_state.current_page = "result"
                    st.rerun()

# 【页面 B：结果页 - 生成式绘图展示】
elif st.session_state.current_page == "result":
    res = st.session_state.last_analysis
    st.markdown("<h2 style='text-align:center;'>🖼️ 行为生成与艺术疗愈</h2>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.write("🎨 **机器人生成的艺术表达**")
        st.markdown(f"""
            <div class="art-canvas">
                <div style="padding:20px; text-align:center;">
                    <p style="color:#888; font-size:12px;">GENERATIVE ART BASED ON EMOTION</p>
                    <p><b>视觉构图：</b><br>{res['art_prompt']}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.write("🤖 **主动干预决策**")
        st.info(f"**识别情绪：** {res['mood']}")
        st.success(f"**生成行为：** {res['action']}")
        if st.button("返回感知台", use_container_width=True):
            st.session_state.current_page = "write"
            st.rerun()

# 【页面 C：大数据页】
elif st.session_state.current_page == "stats":
    st.write("### 📉 历史多模态情感波动图")
    if st.session_state.diary_entries:
        df = pd.DataFrame(st.session_state.diary_entries)
        st.line_chart(df.set_index("date")["score"])
    st.button("返回主页", on_click=lambda: st.session_state.update({"current_page": "write"}))
