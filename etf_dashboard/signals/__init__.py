"""
信号管理模块

负责生成和管理投资信号，包括买入信号判断、规则评估和信号解释。
实现基于技术指标的投资决策逻辑。
"""

from .manager import SignalManager

__all__ = ['SignalManager']