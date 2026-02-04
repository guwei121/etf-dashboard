"""
系统集成器

负责协调各个模块的初始化、连接和数据流转。
提供统一的系统入口点和模块间的通信机制。
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from etf_dashboard.config import get_config
from etf_dashboard.data import DataLoader
from etf_dashboard.indicators import TechnicalIndicators
from etf_dashboard.signals import SignalManager
from etf_dashboard.portfolio import PortfolioManager

from .error_handler import GlobalErrorHandler, ErrorCategory, ErrorSeverity, error_handler
from .data_flow import DataFlowManager


class SystemIntegrator:
    """系统集成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        
        # 错误处理和数据流管理
        self.error_handler = GlobalErrorHandler()
        self.data_flow_manager = DataFlowManager()
        
        # 系统组件
        self.components = {}
        self.component_status = {}
        
        # 初始化状态
        self.is_initialized = False
        self.initialization_time = None
        self.initialization_errors = []
    
    @error_handler(
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.CRITICAL,
        user_message="系统初始化失败",
        recovery_suggestion="检查配置文件和依赖项"
    )
    def initialize_system(self) -> Dict[str, Any]:
        """
        初始化整个系统
        
        Returns:
            初始化结果字典
        """
        self.logger.info("开始初始化ETF投资仪表盘系统...")
        
        try:
            # 创建必要的目录
            self._setup_directories()
            
            # 初始化各个组件
            self._initialize_components()
            
            # 验证组件连接
            self._verify_component_connections()
            
            # 设置数据流
            self._setup_data_flows()
            
            # 标记初始化完成
            self.is_initialized = True
            self.initialization_time = datetime.now()
            
            self.logger.info("系统初始化完成")
            
            return {
                'success': True,
                'message': '系统初始化成功',
                'components': list(self.components.keys()),
                'initialization_time': self.initialization_time.isoformat(),
                'errors': self.initialization_errors
            }
            
        except Exception as e:
            self.initialization_errors.append(str(e))
            self.logger.error(f"系统初始化失败: {str(e)}")
            raise
    
    def _setup_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.config.data.cache_dir,
            os.path.dirname(self.config.logging.file_path),
            os.path.dirname(self.config.portfolio.config_file),
            "config",
            "data",
            "logs"
        ]
        
        for directory in directories:
            if directory:  # 避免空字符串
                try:
                    os.makedirs(directory, exist_ok=True)
                    self.logger.debug(f"目录创建成功: {directory}")
                except Exception as e:
                    self.logger.warning(f"目录创建失败 {directory}: {str(e)}")
        
        self.logger.info("目录结构设置完成")
    
    def _initialize_components(self):
        """初始化各个系统组件"""
        component_configs = [
            ('data_loader', DataLoader, {
                'cache_dir': self.config.data.cache_dir,
                'config': self.config.data.__dict__
            }),
            ('technical_indicators', TechnicalIndicators, {}),
            ('signal_manager', SignalManager, {}),
            ('portfolio_manager', PortfolioManager, {'config_file': self.config.portfolio.config_file})
        ]
        
        for name, component_class, kwargs in component_configs:
            try:
                self.logger.info(f"初始化组件: {name}")
                component = component_class(**kwargs)
                self.components[name] = component
                self.component_status[name] = 'initialized'
                self.logger.info(f"组件 {name} 初始化成功")
                
            except Exception as e:
                error_msg = f"组件 {name} 初始化失败: {str(e)}"
                self.initialization_errors.append(error_msg)
                self.component_status[name] = 'failed'
                self.logger.error(error_msg)
                
                # 对于关键组件，抛出异常
                if name in ['data_loader', 'technical_indicators']:
                    raise RuntimeError(error_msg) from e
    
    def _verify_component_connections(self):
        """验证组件间的连接"""
        self.logger.info("验证组件连接...")
        
        # 检查数据加载器
        if 'data_loader' in self.components:
            try:
                # 测试获取ETF列表
                etf_list = self.components['data_loader'].get_etf_list("A")
                if etf_list:
                    self.logger.info(f"数据加载器连接正常，获取到 {len(etf_list)} 个ETF")
                else:
                    self.logger.warning("数据加载器连接异常，未获取到ETF数据")
            except Exception as e:
                self.logger.error(f"数据加载器连接测试失败: {str(e)}")
        
        # 检查技术指标计算器
        if 'technical_indicators' in self.components:
            try:
                # 测试技术指标计算
                import pandas as pd
                test_data = pd.Series([100, 101, 102, 103, 104])
                ma_result = self.components['technical_indicators'].calculate_moving_averages(
                    test_data, [3, 5]
                )
                if not ma_result.empty:
                    self.logger.info("技术指标计算器连接正常")
                else:
                    self.logger.warning("技术指标计算器连接异常")
            except Exception as e:
                self.logger.error(f"技术指标计算器连接测试失败: {str(e)}")
        
        # 检查信号管理器
        if 'signal_manager' in self.components:
            try:
                # 测试信号生成（使用模拟数据）
                import pandas as pd
                test_data = pd.DataFrame({
                    'close': [100, 101, 102, 103, 104],
                    'volume': [1000, 1100, 1200, 1300, 1400]
                })
                signal = self.components['signal_manager'].generate_buy_signal("159919", test_data)
                if signal:
                    self.logger.info("信号管理器连接正常")
                else:
                    self.logger.warning("信号管理器连接异常")
            except Exception as e:
                self.logger.error(f"信号管理器连接测试失败: {str(e)}")
        
        # 检查组合管理器
        if 'portfolio_manager' in self.components:
            try:
                # 测试组合配置
                config = self.components['portfolio_manager'].get_portfolio_config()
                self.logger.info("组合管理器连接正常")
            except Exception as e:
                self.logger.error(f"组合管理器连接测试失败: {str(e)}")
        
        self.logger.info("组件连接验证完成")
    
    def _setup_data_flows(self):
        """设置数据流"""
        self.logger.info("设置数据流...")
        
        # 注册数据流转换器和验证器
        # 这里可以根据需要添加更多的数据流设置
        
        self.logger.info("数据流设置完成")
    
    def get_component(self, name: str) -> Optional[Any]:
        """
        获取系统组件
        
        Args:
            name: 组件名称
            
        Returns:
            组件实例或None
        """
        return self.components.get(name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            系统状态字典
        """
        return {
            'is_initialized': self.is_initialized,
            'initialization_time': self.initialization_time.isoformat() if self.initialization_time else None,
            'components': {
                name: {
                    'status': self.component_status.get(name, 'unknown'),
                    'type': type(component).__name__
                }
                for name, component in self.components.items()
            },
            'initialization_errors': self.initialization_errors,
            'error_statistics': self.error_handler.get_error_statistics(),
            'data_flow_statistics': self.data_flow_manager.get_flow_statistics()
        }
    
    @error_handler(
        category=ErrorCategory.DATA_ACCESS,
        severity=ErrorSeverity.MEDIUM,
        user_message="ETF数据获取失败",
        recovery_suggestion="检查网络连接或使用缓存数据"
    )
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[Any]:
        """
        获取ETF数据（集成接口）
        
        Args:
            symbol: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            ETF数据或None
        """
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")
        
        data_loader = self.get_component('data_loader')
        if not data_loader:
            raise RuntimeError("数据加载器未初始化")
        
        # 使用数据流管理器处理请求
        request = self.data_flow_manager.request_data(
            source_module='data_loader',
            target_module='system',
            data_type='etf_data',
            parameters={
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date
            }
        )
        
        if request.status.value == 'completed' or request.status.value == 'cached':
            return request.result
        else:
            self.logger.error(f"ETF数据获取失败: {request.error}")
            return None
    
    @error_handler(
        category=ErrorCategory.CALCULATION,
        severity=ErrorSeverity.MEDIUM,
        user_message="技术指标计算失败",
        recovery_suggestion="检查输入数据的有效性"
    )
    def calculate_technical_indicators(self, data: Any, symbol: str) -> Optional[Dict[str, Any]]:
        """
        计算技术指标（集成接口）
        
        Args:
            data: 价格数据
            symbol: ETF代码
            
        Returns:
            技术指标数据或None
        """
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")
        
        indicators = self.get_component('technical_indicators')
        if not indicators:
            raise RuntimeError("技术指标计算器未初始化")
        
        try:
            # 计算各种技术指标
            ma_data = indicators.calculate_moving_averages(
                data['close'], 
                self.config.indicators.ma_periods
            )
            
            rsi = indicators.calculate_rsi(data['close'])
            max_drawdown = indicators.calculate_max_drawdown(data['close'])
            trend_status = indicators.get_trend_status(ma_data)
            
            return {
                'symbol': symbol,
                'ma_data': ma_data,
                'rsi': rsi,
                'max_drawdown': max_drawdown,
                'trend_status': trend_status
            }
            
        except Exception as e:
            self.logger.error(f"技术指标计算失败 {symbol}: {str(e)}")
            return None
    
    @error_handler(
        category=ErrorCategory.CALCULATION,
        severity=ErrorSeverity.MEDIUM,
        user_message="买入信号生成失败",
        recovery_suggestion="检查技术指标数据"
    )
    def generate_buy_signal(self, symbol: str, data: Any = None) -> Optional[Dict[str, Any]]:
        """
        生成买入信号（集成接口）
        
        Args:
            symbol: ETF代码
            data: 价格数据（可选）
            
        Returns:
            买入信号数据或None
        """
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")
        
        signal_manager = self.get_component('signal_manager')
        if not signal_manager:
            raise RuntimeError("信号管理器未初始化")
        
        try:
            # 如果没有提供数据，尝试获取数据
            if data is None:
                data_loader = self.get_component('data_loader')
                if data_loader:
                    from datetime import datetime, timedelta
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                    data = data_loader.get_etf_data(symbol, start_date, end_date)
            
            signal = signal_manager.generate_buy_signal(symbol, data)
            return {
                'symbol': symbol,
                'is_allowed': signal.is_allowed,
                'confidence': signal.confidence,
                'reasons': signal.reasons,
                'timestamp': signal.timestamp
            }
            
        except Exception as e:
            self.logger.error(f"买入信号生成失败 {symbol}: {str(e)}")
            return None
    
    @error_handler(
        category=ErrorCategory.DATA_ACCESS,
        severity=ErrorSeverity.LOW,
        user_message="组合数据获取失败",
        recovery_suggestion="检查组合配置文件"
    )
    def get_portfolio_data(self) -> Optional[Dict[str, Any]]:
        """
        获取组合数据（集成接口）
        
        Returns:
            组合数据或None
        """
        if not self.is_initialized:
            raise RuntimeError("系统未初始化")
        
        portfolio_manager = self.get_component('portfolio_manager')
        if not portfolio_manager:
            raise RuntimeError("组合管理器未初始化")
        
        try:
            config = portfolio_manager.get_portfolio_config()
            if config:
                return {
                    'etf_weights': config.etf_weights,
                    'rebalance_threshold': config.rebalance_threshold,
                    'created_at': config.created_at
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"组合数据获取失败: {str(e)}")
            return None
    
    def shutdown_system(self):
        """关闭系统"""
        self.logger.info("开始关闭系统...")
        
        try:
            # 清理缓存
            self.data_flow_manager.clear_cache()
            
            # 保存配置
            self.config.save_config()
            
            # 清理组件
            self.components.clear()
            self.component_status.clear()
            
            # 重置状态
            self.is_initialized = False
            self.initialization_time = None
            
            self.logger.info("系统关闭完成")
            
        except Exception as e:
            self.logger.error(f"系统关闭失败: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        系统健康检查
        
        Returns:
            健康检查结果
        """
        health_status = {
            'overall_status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'issues': []
        }
        
        # 检查系统初始化状态
        if not self.is_initialized:
            health_status['overall_status'] = 'unhealthy'
            health_status['issues'].append('系统未初始化')
        
        # 检查各个组件
        for name, component in self.components.items():
            try:
                # 简单的组件健康检查
                if hasattr(component, 'health_check'):
                    component_health = component.health_check()
                else:
                    component_health = {'status': 'unknown', 'message': '组件未提供健康检查方法'}
                
                health_status['components'][name] = component_health
                
                if component_health.get('status') != 'healthy':
                    health_status['overall_status'] = 'degraded'
                    health_status['issues'].append(f'组件 {name} 状态异常')
                    
            except Exception as e:
                health_status['components'][name] = {
                    'status': 'error',
                    'message': str(e)
                }
                health_status['overall_status'] = 'unhealthy'
                health_status['issues'].append(f'组件 {name} 健康检查失败: {str(e)}')
        
        return health_status


# 全局系统集成器实例
system_integrator = SystemIntegrator()