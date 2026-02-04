"""
Streamlit应用模块

包含ETF投资仪表盘的Web界面实现，使用Streamlit框架构建。
提供多页面应用结构和交互式数据可视化功能。
"""

from .dashboard import DashboardApp

__all__ = ['DashboardApp']