"""
数据流管理器

负责管理系统各模块间的数据流转，确保数据的一致性和完整性。
提供数据缓存、验证和转换功能。
"""

import logging
import pandas as pd
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .error_handler import GlobalErrorHandler, ErrorCategory, ErrorSeverity


class DataFlowStatus(Enum):
    """数据流状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class DataFlowRequest:
    """数据流请求"""
    request_id: str
    source_module: str
    target_module: str
    data_type: str
    parameters: Dict[str, Any]
    timestamp: datetime
    status: DataFlowStatus = DataFlowStatus.PENDING
    result: Any = None
    error: Optional[str] = None


class DataFlowManager:
    """数据流管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_handler = GlobalErrorHandler()
        
        # 数据流历史记录
        self.flow_history: List[DataFlowRequest] = []
        
        # 数据缓存
        self.data_cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # 数据转换器
        self.data_transformers: Dict[str, Callable] = {}
        
        # 数据验证器
        self.data_validators: Dict[str, Callable] = {}
        
        # 注册默认转换器和验证器
        self._register_default_transformers()
        self._register_default_validators()
    
    def _register_default_transformers(self):
        """注册默认数据转换器"""
        
        # ETF数据转换器
        self.register_transformer('etf_data', self._transform_etf_data)
        
        # 技术指标数据转换器
        self.register_transformer('technical_indicators', self._transform_technical_indicators)
        
        # 信号数据转换器
        self.register_transformer('buy_signal', self._transform_buy_signal)
        
        # 组合数据转换器
        self.register_transformer('portfolio_data', self._transform_portfolio_data)
    
    def _register_default_validators(self):
        """注册默认数据验证器"""
        
        # ETF数据验证器
        self.register_validator('etf_data', self._validate_etf_data)
        
        # 技术指标数据验证器
        self.register_validator('technical_indicators', self._validate_technical_indicators)
        
        # 信号数据验证器
        self.register_validator('buy_signal', self._validate_buy_signal)
        
        # 组合数据验证器
        self.register_validator('portfolio_data', self._validate_portfolio_data)
    
    def register_transformer(self, data_type: str, transformer: Callable):
        """
        注册数据转换器
        
        Args:
            data_type: 数据类型
            transformer: 转换函数
        """
        self.data_transformers[data_type] = transformer
        self.logger.debug(f"已注册数据转换器: {data_type}")
    
    def register_validator(self, data_type: str, validator: Callable):
        """
        注册数据验证器
        
        Args:
            data_type: 数据类型
            validator: 验证函数
        """
        self.data_validators[data_type] = validator
        self.logger.debug(f"已注册数据验证器: {data_type}")
    
    def request_data(
        self,
        source_module: str,
        target_module: str,
        data_type: str,
        parameters: Dict[str, Any],
        use_cache: bool = True,
        cache_ttl: int = 3600  # 缓存时间（秒）
    ) -> DataFlowRequest:
        """
        请求数据流转
        
        Args:
            source_module: 源模块名称
            target_module: 目标模块名称
            data_type: 数据类型
            parameters: 请求参数
            use_cache: 是否使用缓存
            cache_ttl: 缓存生存时间
            
        Returns:
            数据流请求对象
        """
        try:
            # 生成请求ID
            request_id = f"{source_module}_{target_module}_{data_type}_{datetime.now().timestamp()}"
            
            # 创建请求对象
            request = DataFlowRequest(
                request_id=request_id,
                source_module=source_module,
                target_module=target_module,
                data_type=data_type,
                parameters=parameters,
                timestamp=datetime.now()
            )
            
            # 检查缓存
            if use_cache:
                cached_data = self._get_cached_data(data_type, parameters, cache_ttl)
                if cached_data is not None:
                    request.status = DataFlowStatus.CACHED
                    request.result = cached_data
                    self.flow_history.append(request)
                    self.logger.debug(f"使用缓存数据: {request_id}")
                    return request
            
            # 处理数据请求
            request.status = DataFlowStatus.PROCESSING
            self.flow_history.append(request)
            
            # 获取数据
            raw_data = self._fetch_data(source_module, data_type, parameters)
            
            # 验证数据
            if data_type in self.data_validators:
                validation_result = self.data_validators[data_type](raw_data)
                if not validation_result.get('valid', True):
                    raise ValueError(f"数据验证失败: {validation_result.get('message', '未知错误')}")
            
            # 转换数据
            if data_type in self.data_transformers:
                transformed_data = self.data_transformers[data_type](raw_data)
            else:
                transformed_data = raw_data
            
            # 缓存数据
            if use_cache:
                self._cache_data(data_type, parameters, transformed_data)
            
            # 更新请求状态
            request.status = DataFlowStatus.COMPLETED
            request.result = transformed_data
            
            self.logger.info(f"数据流请求完成: {request_id}")
            return request
            
        except Exception as e:
            # 错误处理
            error_result = self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.DATA_ACCESS,
                severity=ErrorSeverity.MEDIUM,
                context={
                    'source_module': source_module,
                    'target_module': target_module,
                    'data_type': data_type,
                    'parameters': parameters
                },
                user_message=f"数据流转失败: {source_module} -> {target_module}",
                recovery_suggestion="检查模块连接和参数设置"
            )
            
            request.status = DataFlowStatus.FAILED
            request.error = error_result['user_message']
            
            self.logger.error(f"数据流请求失败: {request_id}, 错误: {str(e)}")
            return request
    
    def _fetch_data(self, source_module: str, data_type: str, parameters: Dict[str, Any]) -> Any:
        """
        从源模块获取数据
        
        Args:
            source_module: 源模块名称
            data_type: 数据类型
            parameters: 参数
            
        Returns:
            原始数据
        """
        # 这里应该根据source_module调用相应的模块方法
        # 为了简化，这里返回模拟数据
        
        if source_module == 'data_loader':
            if data_type == 'etf_data':
                # 模拟ETF数据
                return self._mock_etf_data(parameters)
            elif data_type == 'etf_list':
                # 模拟ETF列表
                return self._mock_etf_list(parameters)
        
        elif source_module == 'technical_indicators':
            if data_type == 'technical_indicators':
                # 模拟技术指标数据
                return self._mock_technical_indicators(parameters)
        
        elif source_module == 'signal_manager':
            if data_type == 'buy_signal':
                # 模拟买入信号
                return self._mock_buy_signal(parameters)
        
        elif source_module == 'portfolio_manager':
            if data_type == 'portfolio_data':
                # 模拟组合数据
                return self._mock_portfolio_data(parameters)
        
        # 如果没有匹配的模块，返回空数据
        return None
    
    def _get_cached_data(self, data_type: str, parameters: Dict[str, Any], cache_ttl: int) -> Optional[Any]:
        """获取缓存数据"""
        cache_key = self._generate_cache_key(data_type, parameters)
        
        if cache_key in self.data_cache:
            cache_time = self.cache_timestamps.get(cache_key)
            if cache_time and (datetime.now() - cache_time).total_seconds() < cache_ttl:
                return self.data_cache[cache_key]
            else:
                # 缓存过期，删除
                del self.data_cache[cache_key]
                if cache_key in self.cache_timestamps:
                    del self.cache_timestamps[cache_key]
        
        return None
    
    def _cache_data(self, data_type: str, parameters: Dict[str, Any], data: Any):
        """缓存数据"""
        cache_key = self._generate_cache_key(data_type, parameters)
        self.data_cache[cache_key] = data
        self.cache_timestamps[cache_key] = datetime.now()
    
    def _generate_cache_key(self, data_type: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 将参数转换为字符串并排序，确保一致性
        param_str = "_".join(f"{k}:{v}" for k, v in sorted(parameters.items()))
        return f"{data_type}_{hash(param_str)}"
    
    def _transform_etf_data(self, raw_data: Any) -> pd.DataFrame:
        """转换ETF数据"""
        if isinstance(raw_data, pd.DataFrame):
            # 确保数据格式正确
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in raw_data.columns:
                    raise ValueError(f"缺少必需的列: {col}")
            
            # 确保数据类型正确
            for col in required_columns:
                raw_data[col] = pd.to_numeric(raw_data[col], errors='coerce')
            
            # 删除包含NaN的行
            raw_data = raw_data.dropna()
            
            return raw_data
        else:
            raise ValueError("ETF数据必须是DataFrame格式")
    
    def _transform_technical_indicators(self, raw_data: Any) -> Dict[str, Any]:
        """转换技术指标数据"""
        if isinstance(raw_data, dict):
            return raw_data
        else:
            raise ValueError("技术指标数据必须是字典格式")
    
    def _transform_buy_signal(self, raw_data: Any) -> Dict[str, Any]:
        """转换买入信号数据"""
        if isinstance(raw_data, dict):
            # 确保包含必需的字段
            required_fields = ['is_allowed', 'confidence', 'reasons']
            for field in required_fields:
                if field not in raw_data:
                    raise ValueError(f"缺少必需的字段: {field}")
            
            return raw_data
        else:
            raise ValueError("买入信号数据必须是字典格式")
    
    def _transform_portfolio_data(self, raw_data: Any) -> Dict[str, Any]:
        """转换组合数据"""
        if isinstance(raw_data, dict):
            return raw_data
        else:
            raise ValueError("组合数据必须是字典格式")
    
    def _validate_etf_data(self, data: Any) -> Dict[str, Any]:
        """验证ETF数据"""
        try:
            if not isinstance(data, pd.DataFrame):
                return {'valid': False, 'message': 'ETF数据必须是DataFrame格式'}
            
            if data.empty:
                return {'valid': False, 'message': 'ETF数据不能为空'}
            
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                return {'valid': False, 'message': f'缺少必需的列: {missing_columns}'}
            
            # 检查数据的合理性
            if (data['high'] < data['low']).any():
                return {'valid': False, 'message': '存在最高价小于最低价的数据'}
            
            if (data[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
                return {'valid': False, 'message': '存在负数价格或成交量'}
            
            return {'valid': True, 'message': '数据验证通过'}
            
        except Exception as e:
            return {'valid': False, 'message': f'数据验证异常: {str(e)}'}
    
    def _validate_technical_indicators(self, data: Any) -> Dict[str, Any]:
        """验证技术指标数据"""
        try:
            if not isinstance(data, dict):
                return {'valid': False, 'message': '技术指标数据必须是字典格式'}
            
            return {'valid': True, 'message': '数据验证通过'}
            
        except Exception as e:
            return {'valid': False, 'message': f'数据验证异常: {str(e)}'}
    
    def _validate_buy_signal(self, data: Any) -> Dict[str, Any]:
        """验证买入信号数据"""
        try:
            if not isinstance(data, dict):
                return {'valid': False, 'message': '买入信号数据必须是字典格式'}
            
            required_fields = ['is_allowed', 'confidence', 'reasons']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return {'valid': False, 'message': f'缺少必需的字段: {missing_fields}'}
            
            if not isinstance(data['is_allowed'], bool):
                return {'valid': False, 'message': 'is_allowed字段必须是布尔值'}
            
            if not isinstance(data['confidence'], (int, float)) or not 0 <= data['confidence'] <= 1:
                return {'valid': False, 'message': 'confidence字段必须是0到1之间的数值'}
            
            if not isinstance(data['reasons'], list):
                return {'valid': False, 'message': 'reasons字段必须是列表'}
            
            return {'valid': True, 'message': '数据验证通过'}
            
        except Exception as e:
            return {'valid': False, 'message': f'数据验证异常: {str(e)}'}
    
    def _validate_portfolio_data(self, data: Any) -> Dict[str, Any]:
        """验证组合数据"""
        try:
            if not isinstance(data, dict):
                return {'valid': False, 'message': '组合数据必须是字典格式'}
            
            return {'valid': True, 'message': '数据验证通过'}
            
        except Exception as e:
            return {'valid': False, 'message': f'数据验证异常: {str(e)}'}
    
    def _mock_etf_data(self, parameters: Dict[str, Any]) -> pd.DataFrame:
        """模拟ETF数据"""
        # 这里应该调用实际的数据加载器
        # 为了演示，返回空的DataFrame
        return pd.DataFrame()
    
    def _mock_etf_list(self, parameters: Dict[str, Any]) -> List[Dict[str, str]]:
        """模拟ETF列表"""
        return []
    
    def _mock_technical_indicators(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """模拟技术指标数据"""
        return {}
    
    def _mock_buy_signal(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """模拟买入信号"""
        return {
            'is_allowed': False,
            'confidence': 0.0,
            'reasons': []
        }
    
    def _mock_portfolio_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """模拟组合数据"""
        return {}
    
    def get_flow_statistics(self) -> Dict[str, Any]:
        """获取数据流统计信息"""
        if not self.flow_history:
            return {
                'total_requests': 0,
                'by_status': {},
                'by_data_type': {},
                'recent_requests': []
            }
        
        # 按状态统计
        by_status = {}
        for request in self.flow_history:
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # 按数据类型统计
        by_data_type = {}
        for request in self.flow_history:
            data_type = request.data_type
            by_data_type[data_type] = by_data_type.get(data_type, 0) + 1
        
        # 最近的请求
        recent_requests = [
            {
                'request_id': request.request_id,
                'source_module': request.source_module,
                'target_module': request.target_module,
                'data_type': request.data_type,
                'status': request.status.value,
                'timestamp': request.timestamp.isoformat()
            }
            for request in self.flow_history[-10:]  # 最近10个请求
        ]
        
        return {
            'total_requests': len(self.flow_history),
            'by_status': by_status,
            'by_data_type': by_data_type,
            'cache_size': len(self.data_cache),
            'recent_requests': recent_requests
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.data_cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("数据流缓存已清空")
    
    def clear_history(self):
        """清空历史记录"""
        self.flow_history.clear()
        self.logger.info("数据流历史记录已清空")