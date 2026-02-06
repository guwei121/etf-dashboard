"""
ETF投资仪表盘主入口
"""
import streamlit as st
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 页面配置 (必须是第一个 Streamlit 命令)
st.set_page_config(
    page_title="ETF 智投仪表盘",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': "# ETF 智能投资分析系统 v1.0"
    }
)

def init_session_state():
    """初始化全局会话状态"""
    defaults = {
        'current_page': 'overview',
        'selected_etf': None,
        'etf_list': [],
        'last_update': None,
        'portfolio_data': {}
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def main():
    try:
        init_session_state()
        from etf_dashboard.app.dashboard import DashboardApp
        app = DashboardApp()
        app.run()
    except Exception as e:
        st.error("系统启动遭遇严重错误")
        with st.expander("错误详情"):
            st.exception(e)

if __name__ == "__main__":
    main()