"""
ETF投资仪表盘主入口

这是应用的主入口文件，负责初始化和启动Streamlit应用。
"""

import streamlit as st
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置页面配置（必须在其他streamlit命令之前）
if 'page_config_set' not in st.session_state:
    st.set_page_config(
        page_title="ETF投资仪表盘",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.session_state.page_config_set = True

# 初始化会话状态
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'overview'

if 'selected_etf' not in st.session_state:
    st.session_state.selected_etf = None

if 'etf_list' not in st.session_state:
    st.session_state.etf_list = []

if 'last_update' not in st.session_state:
    st.session_state.last_update = None

if 'use_fallback_data' not in st.session_state:
    st.session_state.use_fallback_data = False

# 导入并运行应用
try:
    from etf_dashboard.app.dashboard import DashboardApp
    
    # 创建并运行应用
    app = DashboardApp()
    app.run()
    
except Exception as e:
    st.error(f"应用启动失败: {str(e)}")
    
    # 显示错误详情
    with st.expander("🔧 错误详情", expanded=False):
        st.code(str(e))
    
    # 提供恢复建议
    st.info("💡 建议:")
    st.markdown("""
    1. 检查Python环境和依赖包是否正确安装
    2. 确认配置文件是否存在且格式正确
    3. 检查网络连接是否正常
    4. 尝试重新启动应用
    """)
    
    # 重启按钮
    if st.button("🔄 重新启动应用"):
        st.rerun()