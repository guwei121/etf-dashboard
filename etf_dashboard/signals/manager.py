"""
信号管理器

负责生成投资信号，实现买入允许规则的综合判断。
基于技术指标状态生成明确的买入或禁止信号，并提供详细的判断原因。
"""

import logging
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

from ..models import (
    BuySignal, TrendCondition, RSICondition, DrawdownCondition, 
    TechnicalData, PriceData
)
from ..indicators import TechnicalIndicators


class SignalManager:
    """投资信号生成和管理组件"""
    
    def __init__(self):
        """初始化信号管理器"""
        self.logger = logging.getLogger(__name__)
        self.indicators = TechnicalIndicators()
        
        # 信号规则配置
        self.config = {
            'rsi_overbought_threshold': 70,
            'rsi_oversold_threshold': 30,
            'rsi_neutral_threshold': 50,
            'max_drawdown_threshold': 0.20,  # 20%
            'trend_strength_threshold': 0.6
        }
    
    def generate_buy_signal(self, symbol: str, data: PriceData) -> Optional[BuySignal]:
        """
        生成买入信号
        
        Args:
            symbol: ETF代码
            data: 价格数据
            
        Returns:
            买入信号对象
        """
        try:
            if data is None or data.empty:
                self.logger.error(f"价格数据为空: {symbol}")
                return None
            
            # 计算技术指标
            technical_data = self.indicators.calculate_all_indicators(data, symbol)
            if technical_data is None:
                self.logger.error(f"技术指标计算失败: {symbol}")
                return None
            
            # 评估各项条件
            trend_condition = self.evaluate_trend_condition(technical_data)
            rsi_condition = self.evaluate_rsi_condition(technical_data)
            drawdown_condition = self.evaluate_drawdown_condition(technical_data)
            
            # 综合判断买入信号
            is_allowed, confidence, reasons = self._evaluate_buy_conditions(
                trend_condition, rsi_condition, drawdown_condition
            )
            
            # 创建买入信号
            signal = BuySignal(
                symbol=symbol,
                is_allowed=is_allowed,
                confidence=confidence,
                reasons=reasons,
                timestamp=pd.Timestamp.now()
            )
            
            self.logger.info(f"买入信号生成完成 {symbol}: {'允许' if is_allowed else '禁止'}")
            return signal
            
        except Exception as e:
            self.logger.error(f"买入信号生成失败 {symbol}: {str(e)}")
            return None
    
    def evaluate_trend_condition(self, technical_data: TechnicalData) -> TrendCondition:
        """
        评估趋势条件
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            趋势条件对象
        """
        try:
            trend_status = technical_data.trend_status
            
            # 检查移动平均线排列
            ma_alignment = self._check_ma_alignment(technical_data)
            
            # 计算趋势强度
            strength = self._calculate_trend_strength(technical_data)
            
            condition = TrendCondition(
                status=trend_status,
                ma_alignment=ma_alignment,
                strength=strength
            )
            
            self.logger.debug(f"趋势条件评估: {trend_status}, 排列: {ma_alignment}, 强度: {strength:.2f}")
            return condition
            
        except Exception as e:
            self.logger.error(f"趋势条件评估失败: {str(e)}")
            return TrendCondition(status="震荡", ma_alignment=False, strength=0.0)
    
    def evaluate_rsi_condition(self, technical_data: TechnicalData) -> RSICondition:
        """
        评估RSI条件
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            RSI条件对象
        """
        try:
            if technical_data.rsi.empty:
                return RSICondition(value=50.0, status="正常", is_overbought=False, is_oversold=False)
            
            latest_rsi = technical_data.rsi.iloc[-1]
            
            if pd.isna(latest_rsi):
                latest_rsi = 50.0
            
            # 判断RSI状态
            if latest_rsi > self.config['rsi_overbought_threshold']:
                status = "超买"
                is_overbought = True
                is_oversold = False
            elif latest_rsi < self.config['rsi_oversold_threshold']:
                status = "超卖"
                is_overbought = False
                is_oversold = True
            else:
                status = "正常"
                is_overbought = False
                is_oversold = False
            
            condition = RSICondition(
                value=latest_rsi,
                status=status,
                is_overbought=is_overbought,
                is_oversold=is_oversold
            )
            
            self.logger.debug(f"RSI条件评估: {latest_rsi:.2f}, 状态: {status}")
            return condition
            
        except Exception as e:
            self.logger.error(f"RSI条件评估失败: {str(e)}")
            return RSICondition(value=50.0, status="正常", is_overbought=False, is_oversold=False)
    
    def evaluate_drawdown_condition(self, technical_data: TechnicalData) -> DrawdownCondition:
        """
        评估回撤条件
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            回撤条件对象
        """
        try:
            max_drawdown = technical_data.max_drawdown
            threshold = self.config['max_drawdown_threshold']
            is_excessive = max_drawdown > threshold
            
            condition = DrawdownCondition(
                value=max_drawdown,
                is_excessive=is_excessive,
                threshold=threshold
            )
            
            self.logger.debug(f"回撤条件评估: {max_drawdown:.4f}, 过度: {is_excessive}")
            return condition
            
        except Exception as e:
            self.logger.error(f"回撤条件评估失败: {str(e)}")
            return DrawdownCondition(value=0.0, is_excessive=False)
    
    def get_signal_explanation(self, signal: BuySignal) -> str:
        """
        获取信号解释
        
        Args:
            signal: 买入信号
            
        Returns:
            详细的信号解释文本
        """
        try:
            explanation = f"ETF {signal.symbol} 买入信号分析:\n\n"
            explanation += f"结论: {'✅ 允许买入' if signal.is_allowed else '❌ 禁止买入'}\n"
            explanation += f"信心度: {signal.confidence:.1%}\n"
            explanation += f"生成时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            explanation += "判断依据:\n"
            for i, reason in enumerate(signal.reasons, 1):
                explanation += f"{i}. {reason}\n"
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"信号解释生成失败: {str(e)}")
            return f"信号解释生成失败: {str(e)}"
    
    def _evaluate_buy_conditions(self, trend_condition: TrendCondition, 
                               rsi_condition: RSICondition, 
                               drawdown_condition: DrawdownCondition) -> tuple:
        """
        评估买入条件
        
        Args:
            trend_condition: 趋势条件
            rsi_condition: RSI条件
            drawdown_condition: 回撤条件
            
        Returns:
            (是否允许买入, 信心度, 原因列表)
        """
        reasons = []
        is_allowed = True
        confidence = 1.0
        
        # 规则1: 回撤检查（优先级最高）
        if drawdown_condition.is_excessive:
            is_allowed = False
            confidence = 0.0
            reasons.append(f"最大回撤 {drawdown_condition.value:.1%} 超过阈值 {drawdown_condition.threshold:.1%}，禁止买入")
            return is_allowed, confidence, reasons
        else:
            reasons.append(f"最大回撤 {drawdown_condition.value:.1%} 在可接受范围内")
        
        # 规则2: 趋势和RSI综合判断
        if trend_condition.status == "上升":
            if rsi_condition.value < self.config['rsi_overbought_threshold']:
                reasons.append(f"趋势上升且RSI({rsi_condition.value:.1f}) < 70，符合买入条件")
                confidence *= 0.9  # 上升趋势高信心
            else:
                is_allowed = False
                confidence = 0.2
                reasons.append(f"趋势上升但RSI({rsi_condition.value:.1f}) >= 70，超买状态禁止买入")
        
        elif trend_condition.status == "震荡":
            if rsi_condition.value < self.config['rsi_neutral_threshold']:
                reasons.append(f"趋势震荡且RSI({rsi_condition.value:.1f}) < 50，符合买入条件")
                confidence *= 0.7  # 震荡趋势中等信心
            else:
                is_allowed = False
                confidence = 0.3
                reasons.append(f"趋势震荡但RSI({rsi_condition.value:.1f}) >= 50，不符合买入条件")
        
        elif trend_condition.status == "下降":
            is_allowed = False
            confidence = 0.1
            reasons.append(f"趋势下降，禁止买入")
        
        # 调整信心度基于趋势强度
        if is_allowed:
            confidence *= (0.5 + 0.5 * trend_condition.strength)
        
        # 确保信心度在合理范围内
        confidence = max(0.0, min(1.0, confidence))
        
        return is_allowed, confidence, reasons
    
    def _check_ma_alignment(self, technical_data: TechnicalData) -> bool:
        """
        检查移动平均线排列
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            是否为良好的均线排列
        """
        try:
            if (technical_data.ma5.empty or technical_data.ma20.empty or 
                technical_data.ma60.empty):
                return False
            
            ma5 = technical_data.ma5.iloc[-1]
            ma20 = technical_data.ma20.iloc[-1]
            ma30 = technical_data.ma60.iloc[-1]  # ma60字段现在存储MA30数据
            
            if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma30):
                return False
            
            # 多头排列或空头排列都算作良好排列
            return (ma5 > ma20 > ma30) or (ma5 < ma20 < ma30)
            
        except Exception as e:
            self.logger.error(f"均线排列检查失败: {str(e)}")
            return False
    
    def _calculate_trend_strength(self, technical_data: TechnicalData) -> float:
        """
        计算趋势强度
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            趋势强度 (0-1)
        """
        try:
            if (technical_data.ma5.empty or technical_data.ma20.empty or 
                technical_data.ma60.empty):
                return 0.0
            
            ma5 = technical_data.ma5.iloc[-1]
            ma20 = technical_data.ma20.iloc[-1]
            ma30 = technical_data.ma60.iloc[-1]  # ma60字段现在存储MA30数据
            
            if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma30):
                return 0.0
            
            # 计算均线间的相对差距
            if technical_data.trend_status == "上升":
                # 上升趋势：MA5 > MA20 > MA30
                strength1 = (ma5 - ma20) / ma20 if ma20 > 0 else 0
                strength2 = (ma20 - ma30) / ma30 if ma30 > 0 else 0
                strength = (strength1 + strength2) / 2
            elif technical_data.trend_status == "下降":
                # 下降趋势：MA5 < MA20 < MA30
                strength1 = (ma20 - ma5) / ma5 if ma5 > 0 else 0
                strength2 = (ma30 - ma20) / ma20 if ma20 > 0 else 0
                strength = (strength1 + strength2) / 2
            else:
                # 震荡趋势
                strength = 0.0
            
            # 标准化到0-1范围
            strength = min(1.0, max(0.0, strength * 10))  # 放大10倍后截断
            
            return strength
            
        except Exception as e:
            self.logger.error(f"趋势强度计算失败: {str(e)}")
            return 0.0