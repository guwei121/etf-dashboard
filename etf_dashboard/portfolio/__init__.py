"""
投资组合管理模块

负责管理ETF投资组合的配置、监控和再平衡建议。
提供组合权重计算、偏离度分析和价值评估功能。
"""

from .manager import PortfolioManager

__all__ = ['PortfolioManager']