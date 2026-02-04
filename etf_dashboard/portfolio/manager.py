"""
投资组合管理器

负责管理ETF投资组合的配置、监控当前持仓状态、计算偏离度并生成再平衡建议。
支持组合配置的增删改查操作和价值计算。
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os

from ..models import (
    PortfolioConfig, PortfolioStatus, RebalanceAction, PriceData
)


class PortfolioManager:
    """投资组合管理组件"""
    
    def __init__(self, config_file: str = "data/portfolio_config.json"):
        """
        初始化组合管理器
        
        Args:
            config_file: 组合配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.portfolio_config: Optional[PortfolioConfig] = None
        self.current_holdings: Dict[str, float] = {}  # symbol -> quantity
        
        # 创建配置目录
        config_dir = os.path.dirname(config_file)
        if config_dir:  # 只有当目录不为空时才创建
            os.makedirs(config_dir, exist_ok=True)
        
        # 加载现有配置
        self._load_config()
    
    def add_etf_to_portfolio(self, symbol: str, target_weight: float) -> None:
        """
        添加ETF到组合
        
        Args:
            symbol: ETF代码
            target_weight: 目标权重 (0-1)
        """
        try:
            if not 0 <= target_weight <= 1:
                raise ValueError(f"目标权重必须在0到1之间: {target_weight}")
            
            # 初始化组合配置（如果不存在）
            if self.portfolio_config is None:
                # 创建临时配置，不进行权重总和验证
                self.portfolio_config = PortfolioConfig.__new__(PortfolioConfig)
                self.portfolio_config.etf_weights = {symbol: target_weight}
                self.portfolio_config.rebalance_threshold = 0.05
                self.portfolio_config.created_at = pd.Timestamp.now()
            else:
                # 添加或更新ETF权重
                self.portfolio_config.etf_weights[symbol] = target_weight
            
            # 保存配置
            self._save_config()
            
            self.logger.info(f"ETF已添加到组合: {symbol}, 权重: {target_weight:.2%}")
            
        except Exception as e:
            self.logger.error(f"添加ETF到组合失败 {symbol}: {str(e)}")
            raise
    
    def remove_etf_from_portfolio(self, symbol: str) -> None:
        """
        从组合中移除ETF
        
        Args:
            symbol: ETF代码
        """
        try:
            if self.portfolio_config is None:
                raise ValueError("组合配置不存在")
            
            if symbol not in self.portfolio_config.etf_weights:
                raise ValueError(f"ETF {symbol} 不在组合中")
            
            # 移除ETF
            del self.portfolio_config.etf_weights[symbol]
            
            # 移除对应的持仓
            if symbol in self.current_holdings:
                del self.current_holdings[symbol]
            
            # 保存配置
            self._save_config()
            
            self.logger.info(f"ETF已从组合中移除: {symbol}")
            
        except Exception as e:
            self.logger.error(f"从组合移除ETF失败 {symbol}: {str(e)}")
            raise
    
    def update_target_weights(self, weights: Dict[str, float]) -> None:
        """
        更新目标权重
        
        Args:
            weights: ETF权重字典 {symbol: weight}
        """
        try:
            # 验证权重
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(f"权重总和必须为1.0，当前为: {total_weight}")
            
            for symbol, weight in weights.items():
                if not 0 <= weight <= 1:
                    raise ValueError(f"ETF {symbol} 权重 {weight} 必须在0到1之间")
            
            # 更新配置
            if self.portfolio_config is None:
                # 创建新配置，使用正常的构造函数进行验证
                self.portfolio_config = PortfolioConfig(
                    etf_weights=weights,
                    rebalance_threshold=0.05,
                    created_at=pd.Timestamp.now()
                )
            else:
                self.portfolio_config.etf_weights = weights.copy()
                # 手动验证权重总和
                self._validate_weights()
            
            # 保存配置
            self._save_config()
            
            self.logger.info(f"目标权重已更新: {len(weights)} 个ETF")
            
        except Exception as e:
            self.logger.error(f"更新目标权重失败: {str(e)}")
            raise
    
    def update_current_holdings(self, holdings: Dict[str, float]) -> None:
        """
        更新当前持仓
        
        Args:
            holdings: 持仓字典 {symbol: quantity}
        """
        try:
            # 验证持仓数据
            for symbol, quantity in holdings.items():
                if quantity < 0:
                    raise ValueError(f"ETF {symbol} 持仓数量不能为负数: {quantity}")
            
            self.current_holdings = holdings.copy()
            self.logger.info(f"当前持仓已更新: {len(holdings)} 个ETF")
            
        except Exception as e:
            self.logger.error(f"更新当前持仓失败: {str(e)}")
            raise
    
    def calculate_portfolio_deviation(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        计算组合偏离度
        
        Args:
            current_prices: 当前价格字典 {symbol: price}
            
        Returns:
            偏离度字典 {symbol: deviation}
        """
        try:
            if self.portfolio_config is None:
                raise ValueError("组合配置不存在")
            
            # 计算当前权重
            current_weights = self._calculate_current_weights(current_prices)
            
            # 计算偏离度
            deviations = {}
            for symbol in self.portfolio_config.etf_weights:
                target_weight = self.portfolio_config.etf_weights[symbol]
                current_weight = current_weights.get(symbol, 0.0)
                deviation = abs(current_weight - target_weight)
                deviations[symbol] = deviation
            
            self.logger.debug(f"组合偏离度计算完成: {len(deviations)} 个ETF")
            return deviations
            
        except Exception as e:
            self.logger.error(f"计算组合偏离度失败: {str(e)}")
            return {}
    
    def get_rebalance_suggestions(self, current_prices: Dict[str, float], 
                                threshold: Optional[float] = None) -> List[RebalanceAction]:
        """
        获取再平衡建议
        
        Args:
            current_prices: 当前价格字典
            threshold: 偏离阈值，如果为None使用配置中的阈值
            
        Returns:
            再平衡操作列表
        """
        try:
            if self.portfolio_config is None:
                raise ValueError("组合配置不存在")
            
            if threshold is None:
                threshold = self.portfolio_config.rebalance_threshold
            
            # 计算当前权重和偏离度
            current_weights = self._calculate_current_weights(current_prices)
            deviations = self.calculate_portfolio_deviation(current_prices)
            
            # 计算组合总价值
            total_value = self.calculate_portfolio_value(current_prices)
            
            suggestions = []
            
            for symbol in self.portfolio_config.etf_weights:
                target_weight = self.portfolio_config.etf_weights[symbol]
                current_weight = current_weights.get(symbol, 0.0)
                deviation = deviations[symbol]
                
                if deviation > threshold:
                    # 需要再平衡
                    if current_weight > target_weight:
                        action = "卖出"
                        suggested_amount = (current_weight - target_weight) * total_value
                    else:
                        action = "买入"
                        suggested_amount = (target_weight - current_weight) * total_value
                else:
                    action = "持有"
                    suggested_amount = 0.0
                
                suggestion = RebalanceAction(
                    symbol=symbol,
                    action=action,
                    current_weight=current_weight,
                    target_weight=target_weight,
                    deviation=deviation,
                    suggested_amount=suggested_amount
                )
                
                suggestions.append(suggestion)
            
            # 按偏离度排序
            suggestions.sort(key=lambda x: x.deviation, reverse=True)
            
            self.logger.info(f"再平衡建议生成完成: {len(suggestions)} 个ETF")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"生成再平衡建议失败: {str(e)}")
            return []
    
    def calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算组合总价值
        
        Args:
            current_prices: 当前价格字典 {symbol: price}
            
        Returns:
            组合总价值
        """
        try:
            total_value = 0.0
            
            for symbol, quantity in self.current_holdings.items():
                if symbol in current_prices:
                    value = quantity * current_prices[symbol]
                    total_value += value
                else:
                    self.logger.warning(f"缺少ETF价格数据: {symbol}")
            
            self.logger.debug(f"组合总价值: {total_value:.2f}")
            return total_value
            
        except Exception as e:
            self.logger.error(f"计算组合价值失败: {str(e)}")
            return 0.0
    
    def get_portfolio_config(self) -> Optional[PortfolioConfig]:
        """
        获取组合配置
        
        Returns:
            组合配置对象，如果不存在则返回None
        """
        return self.portfolio_config
    
    def get_portfolio_status(self, current_prices: Dict[str, float]) -> Optional[PortfolioStatus]:
        """
        获取组合状态
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            组合状态对象
        """
        try:
            if self.portfolio_config is None:
                return None
            
            current_weights = self._calculate_current_weights(current_prices)
            deviations = self.calculate_portfolio_deviation(current_prices)
            total_value = self.calculate_portfolio_value(current_prices)
            
            # 检查是否需要再平衡
            needs_rebalance = any(
                dev > self.portfolio_config.rebalance_threshold 
                for dev in deviations.values()
            )
            
            status = PortfolioStatus(
                current_weights=current_weights,
                target_weights=self.portfolio_config.etf_weights.copy(),
                deviations=deviations,
                total_value=total_value,
                needs_rebalance=needs_rebalance
            )
            
            return status
            
        except Exception as e:
            self.logger.error(f"获取组合状态失败: {str(e)}")
            return None
    
    def _calculate_current_weights(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        计算当前权重
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            当前权重字典
        """
        try:
            total_value = self.calculate_portfolio_value(current_prices)
            
            if total_value == 0:
                return {symbol: 0.0 for symbol in self.portfolio_config.etf_weights}
            
            current_weights = {}
            for symbol in self.portfolio_config.etf_weights:
                quantity = self.current_holdings.get(symbol, 0.0)
                price = current_prices.get(symbol, 0.0)
                value = quantity * price
                weight = value / total_value
                current_weights[symbol] = weight
            
            return current_weights
            
        except Exception as e:
            self.logger.error(f"计算当前权重失败: {str(e)}")
            return {}
    
    def _validate_weights(self) -> None:
        """验证权重总和"""
        if self.portfolio_config is None:
            return
        
        total_weight = sum(self.portfolio_config.etf_weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"权重总和必须为1.0，当前为: {total_weight}")
    
    def _load_config(self) -> None:
        """加载组合配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 使用__new__创建对象以跳过__post_init__验证
                self.portfolio_config = PortfolioConfig.__new__(PortfolioConfig)
                self.portfolio_config.etf_weights = config_data['etf_weights']
                self.portfolio_config.rebalance_threshold = config_data['rebalance_threshold']
                self.portfolio_config.created_at = pd.to_datetime(config_data['created_at'])
                
                self.logger.info(f"组合配置已加载: {len(self.portfolio_config.etf_weights)} 个ETF")
            else:
                self.logger.info("组合配置文件不存在，将创建新配置")
                
        except Exception as e:
            self.logger.error(f"加载组合配置失败: {str(e)}")
            self.portfolio_config = None
    
    def _save_config(self) -> None:
        """保存组合配置"""
        try:
            if self.portfolio_config is None:
                return
            
            config_data = {
                'etf_weights': self.portfolio_config.etf_weights,
                'rebalance_threshold': self.portfolio_config.rebalance_threshold,
                'created_at': self.portfolio_config.created_at.isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug("组合配置已保存")
            
        except Exception as e:
            self.logger.error(f"保存组合配置失败: {str(e)}")
            raise