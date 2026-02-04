"""
ETF投资仪表盘 - 基于规则的ETF投资决策支持系统

这是一个模块化的金融数据分析系统，通过明确的规则来辅助ETF投资决策。
系统采用分层架构设计，包含数据层、业务逻辑层和表现层。

主要功能:
- ETF数据获取和管理
- 技术指标计算和分析
- 投资信号生成和管理
- 投资组合管理和监控
- 可视化仪表盘界面

作者: ETF Dashboard Team
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "ETF Dashboard Team"

# 导入核心模块
from .data import DataLoader
from .indicators import TechnicalIndicators
from .signals import SignalManager
from .portfolio import PortfolioManager
from .core import GlobalErrorHandler, SystemIntegrator, DataFlowManager
from .models import *

__all__ = [
    'DataLoader',
    'TechnicalIndicators', 
    'SignalManager',
    'PortfolioManager',
    'GlobalErrorHandler',
    'SystemIntegrator',
    'DataFlowManager',
]