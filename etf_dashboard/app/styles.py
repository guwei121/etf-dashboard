# etf_dashboard/app/styles.py

CUSTOM_CSS = """
<style>
    /* 全局背景优化 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* 侧边栏优化 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }

    /* 卡片式容器 */
    .css-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }

    /* 标题样式 */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        color: #2c3e50;
        font-weight: 600;
    }
    
    .page-header {
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #3498db;
    }

    /* 指标卡片增强 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #f0f2f6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* 按钮美化 */
    div.stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }
</style>
"""

def apply_styles():
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def card_container(key=None):
    """创建一个视觉上的卡片容器"""
    import streamlit as st
    return st.container()