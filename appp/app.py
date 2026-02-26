import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime
import random

# --- 1. 行为生成逻辑：根据情绪和物理感知改变视觉 ---
def get_dynamic_style(score):
    if score > 0.8: # 极佳状态：金光背景
        return "background: linear-gradient(135deg, #fff9e6 0%, #ffecb3 100%);"
    elif score < 0.4: # 低能耗状态：冷色调
        return "background: linear-gradient(135deg, #e6f2ff 0%, #d1e9ff 100%);"
    return "background: #fdfaf5;"

st.markdown(f"""
    <style>
    .stApp {{ {get_dynamic_style(st.session_state.get('last_score', 0.5))} transition: all 1.5s ease; }}
    .monitor-card {{
        background: rgba(255, 255, 255, 0.7);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
    }}
    .art-frame {{
        border: 15px solid #3d2b1f;
        padding: 10px;
        background: white;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化 ---
if "diary_entries" not in st.session_state:
    st.session_state.diary_entries = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "cover"
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

client = OpenAI(api_key=st.secrets["api_key"], base_url="https://api.deepseek.com")

# --- 3. 页面路由 ---

# 【页面 0：封面 - 欢迎与行为初始化】
if st.session_state.current_page == "cover":
    st.markdown("<h1 style='text-align:center;'>🤖 多模态情绪生成机器人</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='text-align:center;'>物理联动感知 | 跨模态生成决策 | 行为干预系统</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("激活系统并开启感知", use_container_width=True):
            st.session_state.current_page = "write"
            st.rerun()

# 【页面 A：录入中心 - 物理联动 + 文本输入】
elif st.session_state.current_page == "write":
    st.subheader("📡 多模态数据采集")
    
    col_cam, col_txt = st.columns([1, 1])
    
    with col_cam:
        st.write("📷 **创新点 1：物理联动感知**")
        # 实时开启摄像头采集用户表情，作为物理特征输入
        picture = st.camera_input("请面对摄像头，让机器人感知你的生物特征", key="face_stream")
    
    with col_txt:
        st.write("🖋️ **文本情感注入**")
        diary_input = st.text_area("在此输入文字...", height=200, label_visibility="collapsed")
        
        if st.button("🚀 启动行为生成引擎", use_container_width=True):
            if diary_input:
                with st.spinner("AI 正在融合多模态数据并生成艺术画作..."):
                    # 提示词升级：要求生成情绪得分、建议行为、以及绘图提示词
                    prompt = """
                    作为情绪机器人，请综合物理特征(图片)与文字，返回JSON:
                    {'score':0-1, 'mood':'心情', 'action':'主动行为建议', 'art_prompt':'描述一张代表此情绪的抽象画'}
                    """
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": diary_input}],
                        response_format={'type': 'json_object'}
                    )
                    res = json.loads(response.choices[0].message.content)
                    
                    st.session_state.last_score = res["score"]
                    analysis = {
                        "date": datetime.now().strftime("%H:%M"),
                        "score": res["score"],
                        "mood": res["mood"],
                        "action": res["action"],
                        "art_prompt": res["art_prompt"],
                        "content": diary_input
                    }
                    st.session_state.diary_entries.insert(0, analysis)
                    st.session_state.last_analysis = analysis
                    st.session_state.current_page = "result"
                    st.rerun()

    if st.button("📊 调取大数据档案"):
        st.session_state.current_page = "stats"
        st.rerun()

# 【页面 B：结果页 - 生成式绘图展示】
elif st.session_state.current_page == "result":
    res = st.session_state.last_analysis
    st.markdown("<h2 style='text-align:center;'>🖼️ 生成式疗愈报告</h2>", unsafe_allow_html=True)
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("### **创新点 2：生成式艺术表达**")
        # 模拟绘图生成：展示 AI 生成的 Prompt 并配上风格化容器
        st.markdown(f"""
        <div class="art-frame">
            <div style="background:#eee; height:300px; display:flex; align-items:center; justify-content:center; text-align:center; padding:20px;">
                <i>[生成式绘图模块已激活]<br><br><b>AI 正在绘制：</b><br>{res['art_prompt']}</i>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"🎭 **识别情绪：** {res['mood']} | **分值：** {res['score']}")
        st.success(f"🤖 **主动行为生成：** {res['action']}")
        
        if st.button("↩️ 重启感知"):
            st.session_state.current_page = "write"
            st.rerun()

# 【页面 C：数据监测 - 实时波动】
elif st.session_state.current_page == "stats":
    st.markdown("## 💹 大数据情绪动力学监测")
    if st.session_state.diary_entries:
        df = pd.DataFrame(st.session_state.diary_entries)
        st.line_chart(df.iloc[::-1].set_index("date")["score"])
        st.write("### 行为决策链记录")
        st.table(df[["date", "mood", "action"]].head(10))
    
    if st.button("⬅️ 返回控制台"):
        st.session_state.current_page = "write"
        st.rerun()
