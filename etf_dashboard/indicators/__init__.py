"""
技术指标计算模块

负责计算各种技术指标，包括移动平均线、RSI、最大回撤等。
提供趋势状态判断和技术分析功能。
"""

from .calculator import TechnicalIndicators

__all__ = ['TechnicalIndicators']