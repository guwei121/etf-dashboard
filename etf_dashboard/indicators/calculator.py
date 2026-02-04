"""
技术指标计算器

实现各种技术指标的计算，包括移动平均线、RSI、最大回撤等。
提供趋势状态判断和超买超卖分析功能。
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional

from ..models import TechnicalData, PriceData


class TechnicalIndicators:
    """技术指标计算组件"""
    
    def __init__(self):
        """初始化技术指标计算器"""
        self.logger = logging.getLogger(__name__)
    
    def calculate_moving_averages(self, prices: pd.Series, periods: List[int]) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            prices: 价格序列（通常是收盘价）
            periods: 周期列表，如[5, 20, 60]
            
        Returns:
            包含各周期移动平均线的DataFrame
        """
        try:
            if prices is None or prices.empty:
                raise ValueError("价格序列不能为空")
            
            result = pd.DataFrame(index=prices.index)
            
            for period in periods:
                if period <= 0:
                    raise ValueError(f"移动平均周期必须为正数: {period}")
                
                if len(prices) < period:
                    self.logger.warning(f"数据长度 {len(prices)} 小于MA周期 {period}")
                    result[f'MA{period}'] = np.nan
                else:
                    result[f'MA{period}'] = prices.rolling(window=period, min_periods=period).mean()
            
            self.logger.debug(f"移动平均线计算完成，周期: {periods}")
            return result
            
        except Exception as e:
            self.logger.error(f"移动平均线计算失败: {str(e)}")
            raise
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算相对强弱指数(RSI)
        
        Args:
            prices: 价格序列
            period: 计算周期，默认14
            
        Returns:
            RSI值序列
        """
        try:
            if prices is None or prices.empty:
                raise ValueError("价格序列不能为空")
            
            if period <= 0:
                raise ValueError(f"RSI周期必须为正数: {period}")
            
            if len(prices) < period + 1:
                self.logger.warning(f"数据长度 {len(prices)} 不足以计算RSI{period}")
                return pd.Series(np.nan, index=prices.index)
            
            # 计算价格变化
            delta = prices.diff()
            
            # 分离上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 计算平均收益和平均损失
            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()
            
            # 计算RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # 处理除零情况
            rsi = rsi.fillna(50)  # 当avg_loss为0时，RSI设为50
            
            self.logger.debug(f"RSI计算完成，周期: {period}")
            return rsi
            
        except Exception as e:
            self.logger.error(f"RSI计算失败: {str(e)}")
            raise
    
    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        计算最大回撤百分比
        
        Args:
            prices: 价格序列
            
        Returns:
            最大回撤百分比（0-1之间的值）
        """
        try:
            if prices is None or prices.empty:
                raise ValueError("价格序列不能为空")
            
            # 计算累计最高价
            peak = prices.expanding().max()
            
            # 计算回撤
            drawdown = (peak - prices) / peak
            
            # 最大回撤
            max_drawdown = drawdown.max()
            
            # 处理NaN情况
            if pd.isna(max_drawdown):
                max_drawdown = 0.0
            
            self.logger.debug(f"最大回撤计算完成: {max_drawdown:.4f}")
            return float(max_drawdown)
            
        except Exception as e:
            self.logger.error(f"最大回撤计算失败: {str(e)}")
            raise
    
    def get_trend_status(self, ma_data: pd.DataFrame) -> str:
        """
        判断趋势状态
        
        Args:
            ma_data: 包含移动平均线的DataFrame
            
        Returns:
            趋势状态: "上升", "下降", "震荡"
        """
        try:
            if ma_data is None or ma_data.empty:
                return "震荡"
            
            # 获取最新的移动平均线数值
            latest_data = ma_data.iloc[-1]
            
            # 检查是否有必需的移动平均线
            required_mas = ['MA5', 'MA20', 'MA30']
            missing_mas = [ma for ma in required_mas if ma not in latest_data or pd.isna(latest_data[ma])]
            
            if missing_mas:
                self.logger.warning(f"缺少移动平均线数据: {missing_mas}")
                return "震荡"
            
            ma5 = latest_data['MA5']
            ma20 = latest_data['MA20']
            ma30 = latest_data['MA30']
            
            # 判断趋势
            if ma5 > ma20 > ma30:
                # 多头排列
                trend = "上升"
            elif ma5 < ma20 < ma30:
                # 空头排列
                trend = "下降"
            else:
                # 均线交叉或平行
                trend = "震荡"
            
            self.logger.debug(f"趋势状态判断: {trend} (MA5:{ma5:.2f}, MA20:{ma20:.2f}, MA30:{ma30:.2f})")
            return trend
            
        except Exception as e:
            self.logger.error(f"趋势状态判断失败: {str(e)}")
            return "震荡"
    
    def is_oversold_or_overbought(self, rsi: pd.Series, overbought_threshold: float = 70, 
                                 oversold_threshold: float = 30) -> Tuple[bool, bool]:
        """
        判断是否超买或超卖
        
        Args:
            rsi: RSI序列
            overbought_threshold: 超买阈值，默认70
            oversold_threshold: 超卖阈值，默认30
            
        Returns:
            (是否超卖, 是否超买)
        """
        try:
            if rsi is None or rsi.empty:
                return False, False
            
            # 获取最新RSI值
            latest_rsi = rsi.iloc[-1]
            
            if pd.isna(latest_rsi):
                return False, False
            
            is_oversold = latest_rsi < oversold_threshold
            is_overbought = latest_rsi > overbought_threshold
            
            self.logger.debug(f"RSI状态: {latest_rsi:.2f}, 超卖: {is_oversold}, 超买: {is_overbought}")
            return is_oversold, is_overbought
            
        except Exception as e:
            self.logger.error(f"超买超卖判断失败: {str(e)}")
            return False, False
    
    def calculate_all_indicators(self, data: PriceData, symbol: str) -> Optional[TechnicalData]:
        """
        计算所有技术指标
        
        Args:
            data: 价格数据
            symbol: ETF代码
            
        Returns:
            技术指标数据对象
        """
        try:
            if data is None or data.empty:
                raise ValueError("价格数据不能为空")
            
            if 'close' not in data.columns:
                raise ValueError("价格数据必须包含收盘价列")
            
            close_prices = data['close']
            
            # 计算移动平均线
            ma_data = self.calculate_moving_averages(close_prices, [5, 20, 30])
            
            # 计算RSI
            rsi_data = self.calculate_rsi(close_prices)
            
            # 计算最大回撤
            max_drawdown = self.calculate_max_drawdown(close_prices)
            
            # 判断趋势状态
            trend_status = self.get_trend_status(ma_data)
            
            # 创建技术指标对象
            technical_data = TechnicalData(
                symbol=symbol,
                ma5=ma_data['MA5'] if 'MA5' in ma_data.columns else pd.Series(dtype=float),
                ma20=ma_data['MA20'] if 'MA20' in ma_data.columns else pd.Series(dtype=float),
                ma60=ma_data['MA30'] if 'MA30' in ma_data.columns else pd.Series(dtype=float),  # 使用MA30替代MA60
                rsi=rsi_data,
                max_drawdown=max_drawdown,
                trend_status=trend_status
            )
            
            self.logger.info(f"技术指标计算完成: {symbol}")
            return technical_data
            
        except Exception as e:
            self.logger.error(f"技术指标计算失败 {symbol}: {str(e)}")
            return None
    
    def get_latest_values(self, technical_data: TechnicalData) -> Dict[str, float]:
        """
        获取最新的技术指标数值
        
        Args:
            technical_data: 技术指标数据
            
        Returns:
            最新指标值字典
        """
        try:
            result = {}
            
            # 移动平均线
            if not technical_data.ma5.empty:
                result['MA5'] = technical_data.ma5.iloc[-1]
            if not technical_data.ma20.empty:
                result['MA20'] = technical_data.ma20.iloc[-1]
            if not technical_data.ma60.empty:
                result['MA30'] = technical_data.ma60.iloc[-1]  # ma60字段现在存储MA30数据
            
            # RSI
            if not technical_data.rsi.empty:
                result['RSI'] = technical_data.rsi.iloc[-1]
            
            # 最大回撤
            result['MaxDrawdown'] = technical_data.max_drawdown
            
            # 趋势状态
            result['TrendStatus'] = technical_data.trend_status
            
            return result
            
        except Exception as e:
            self.logger.error(f"获取最新指标值失败: {str(e)}")
            return {}