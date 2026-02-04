"""
数据模型定义

定义系统中使用的核心数据结构，包括ETF数据、技术指标、信号和组合相关的数据模型。
使用dataclass提供类型安全和清晰的数据结构定义。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime


@dataclass
class ETFData:
    """ETF基础数据模型"""
    symbol: str
    name: str
    date: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def __post_init__(self):
        """数据验证"""
        if self.high < self.low:
            raise ValueError(f"最高价 {self.high} 不能小于最低价 {self.low}")
        if self.open < 0 or self.close < 0:
            raise ValueError("价格不能为负数")
        if self.volume < 0:
            raise ValueError("成交量不能为负数")


@dataclass
class TechnicalData:
    """技术指标数据模型"""
    symbol: str
    ma5: pd.Series
    ma20: pd.Series
    ma60: pd.Series
    rsi: pd.Series
    max_drawdown: float
    trend_status: str
    
    def __post_init__(self):
        """数据验证"""
        valid_trends = ["上升", "下降", "震荡"]
        if self.trend_status not in valid_trends:
            raise ValueError(f"趋势状态必须是 {valid_trends} 之一")
        if self.max_drawdown < 0:
            raise ValueError("最大回撤不能为负数")


@dataclass
class BuySignal:
    """买入信号模型"""
    symbol: str
    is_allowed: bool
    confidence: float
    reasons: List[str]
    timestamp: pd.Timestamp
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("信心度必须在0到1之间")
        if not self.reasons:
            raise ValueError("必须提供信号原因")


@dataclass
class TrendCondition:
    """趋势条件模型"""
    status: str  # "上升", "下降", "震荡"
    ma_alignment: bool
    strength: float
    
    def __post_init__(self):
        """数据验证"""
        valid_status = ["上升", "下降", "震荡"]
        if self.status not in valid_status:
            raise ValueError(f"趋势状态必须是 {valid_status} 之一")
        if not 0 <= self.strength <= 1:
            raise ValueError("趋势强度必须在0到1之间")


@dataclass
class RSICondition:
    """RSI条件模型"""
    value: float
    status: str  # "超买", "超卖", "正常"
    is_overbought: bool
    is_oversold: bool
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.value <= 100:
            raise ValueError("RSI值必须在0到100之间")
        valid_status = ["超买", "超卖", "正常"]
        if self.status not in valid_status:
            raise ValueError(f"RSI状态必须是 {valid_status} 之一")


@dataclass
class DrawdownCondition:
    """回撤条件模型"""
    value: float
    is_excessive: bool
    threshold: float = 0.20  # 默认20%阈值
    
    def __post_init__(self):
        """数据验证"""
        if self.value < 0:
            raise ValueError("回撤值不能为负数")
        if self.threshold < 0 or self.threshold > 1:
            raise ValueError("回撤阈值必须在0到1之间")


@dataclass
class PortfolioConfig:
    """投资组合配置模型"""
    etf_weights: Dict[str, float]  # symbol -> target_weight
    rebalance_threshold: float
    created_at: pd.Timestamp
    
    def __post_init__(self):
        """数据验证"""
        # 允许空配置，但如果有配置则验证权重
        if self.etf_weights:
            total_weight = sum(self.etf_weights.values())
            if abs(total_weight - 1.0) > 0.001:  # 允许小的浮点误差
                raise ValueError(f"权重总和必须为1.0，当前为 {total_weight}")
            
            for symbol, weight in self.etf_weights.items():
                if weight < 0 or weight > 1:
                    raise ValueError(f"ETF {symbol} 的权重 {weight} 必须在0到1之间")
        
        if not 0 < self.rebalance_threshold < 1:
            raise ValueError("再平衡阈值必须在0到1之间")


@dataclass
class PortfolioStatus:
    """投资组合状态模型"""
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    deviations: Dict[str, float]
    total_value: float
    needs_rebalance: bool
    
    def __post_init__(self):
        """数据验证"""
        if self.total_value < 0:
            raise ValueError("组合总价值不能为负数")
        
        # 检查权重字典的一致性
        symbols = set(self.current_weights.keys())
        if symbols != set(self.target_weights.keys()):
            raise ValueError("当前权重和目标权重的ETF符号必须一致")
        if symbols != set(self.deviations.keys()):
            raise ValueError("偏离度字典的ETF符号必须与权重字典一致")


@dataclass
class RebalanceAction:
    """再平衡操作模型"""
    symbol: str
    action: str  # "买入", "卖出", "持有"
    current_weight: float
    target_weight: float
    deviation: float
    suggested_amount: float
    
    def __post_init__(self):
        """数据验证"""
        valid_actions = ["买入", "卖出", "持有"]
        if self.action not in valid_actions:
            raise ValueError(f"操作类型必须是 {valid_actions} 之一")
        
        if not 0 <= self.current_weight <= 1:
            raise ValueError("当前权重必须在0到1之间")
        if not 0 <= self.target_weight <= 1:
            raise ValueError("目标权重必须在0到1之间")


# 类型别名定义
PriceData = pd.DataFrame  # 包含OHLCV数据的DataFrame
IndicatorData = pd.DataFrame  # 包含技术指标的DataFrame
ETFList = List[Dict[str, str]]  # ETF列表，每个元素包含symbol和name