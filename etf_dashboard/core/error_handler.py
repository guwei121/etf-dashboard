"""
全局错误处理器

提供统一的错误处理机制，包括错误捕获、日志记录、用户友好的错误提示等。
支持不同类型的错误处理策略和恢复机制。
"""

import logging
import traceback
import functools
from typing import Any, Callable, Dict, Optional, Type, Union
from datetime import datetime
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    DATA_ACCESS = "data_access"
    CALCULATION = "calculation"
    VALIDATION = "validation"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    USER_INPUT = "user_input"
    SYSTEM = "system"


class ErrorInfo:
    """错误信息类"""
    
    def __init__(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any] = None,
        user_message: str = None,
        recovery_suggestion: str = None
    ):
        self.error = error
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_message = user_message or str(error)
        self.recovery_suggestion = recovery_suggestion
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()


class GlobalErrorHandler:
    """全局错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history = []
        self.error_handlers = {}
        self.recovery_strategies = {}
        
        # 注册默认错误处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认错误处理器"""
        
        # 数据访问错误
        self.register_handler(
            ErrorCategory.DATA_ACCESS,
            self._handle_data_access_error
        )
        
        # 计算错误
        self.register_handler(
            ErrorCategory.CALCULATION,
            self._handle_calculation_error
        )
        
        # 验证错误
        self.register_handler(
            ErrorCategory.VALIDATION,
            self._handle_validation_error
        )
        
        # 网络错误
        self.register_handler(
            ErrorCategory.NETWORK,
            self._handle_network_error
        )
        
        # 配置错误
        self.register_handler(
            ErrorCategory.CONFIGURATION,
            self._handle_configuration_error
        )
        
        # 用户输入错误
        self.register_handler(
            ErrorCategory.USER_INPUT,
            self._handle_user_input_error
        )
        
        # 系统错误
        self.register_handler(
            ErrorCategory.SYSTEM,
            self._handle_system_error
        )
    
    def register_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorInfo], Dict[str, Any]]
    ):
        """
        注册错误处理器
        
        Args:
            category: 错误类别
            handler: 处理函数，返回处理结果字典
        """
        self.error_handlers[category] = handler
    
    def register_recovery_strategy(
        self,
        category: ErrorCategory,
        strategy: Callable[[ErrorInfo], Any]
    ):
        """
        注册恢复策略
        
        Args:
            category: 错误类别
            strategy: 恢复策略函数
        """
        self.recovery_strategies[category] = strategy
    
    def handle_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Dict[str, Any] = None,
        user_message: str = None,
        recovery_suggestion: str = None
    ) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            category: 错误类别
            severity: 错误严重程度
            context: 错误上下文信息
            user_message: 用户友好的错误消息
            recovery_suggestion: 恢复建议
            
        Returns:
            处理结果字典
        """
        try:
            # 创建错误信息对象
            error_info = ErrorInfo(
                error=error,
                category=category,
                severity=severity,
                context=context,
                user_message=user_message,
                recovery_suggestion=recovery_suggestion
            )
            
            # 记录错误历史
            self.error_history.append(error_info)
            
            # 记录日志
            self._log_error(error_info)
            
            # 调用对应的错误处理器
            handler = self.error_handlers.get(category, self._handle_generic_error)
            result = handler(error_info)
            
            # 尝试恢复
            if category in self.recovery_strategies:
                try:
                    recovery_result = self.recovery_strategies[category](error_info)
                    result['recovery_result'] = recovery_result
                except Exception as recovery_error:
                    self.logger.error(f"恢复策略执行失败: {str(recovery_error)}")
            
            return result
            
        except Exception as handler_error:
            # 错误处理器本身出错，使用最基本的处理方式
            self.logger.critical(f"错误处理器失败: {str(handler_error)}")
            return {
                'success': False,
                'user_message': '系统发生未知错误，请联系管理员',
                'technical_message': str(error),
                'should_retry': False,
                'fallback_data': None
            }
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        log_message = (
            f"[{error_info.category.value.upper()}] {error_info.user_message}\n"
            f"技术详情: {str(error_info.error)}\n"
            f"上下文: {error_info.context}\n"
            f"恢复建议: {error_info.recovery_suggestion}"
        )
        
        self.logger.log(log_level, log_message)
        
        # 对于严重错误，同时记录完整的堆栈跟踪
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"堆栈跟踪:\n{error_info.traceback}")
    
    def _handle_data_access_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理数据访问错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '数据获取失败，请稍后重试',
            'technical_message': str(error_info.error),
            'should_retry': True,
            'fallback_data': self._get_cached_data(error_info.context),
            'recovery_suggestion': '检查网络连接或使用缓存数据'
        }
    
    def _handle_calculation_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理计算错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '计算过程中发生错误',
            'technical_message': str(error_info.error),
            'should_retry': False,
            'fallback_data': None,
            'recovery_suggestion': '检查输入数据的有效性'
        }
    
    def _handle_validation_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理验证错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '输入数据验证失败',
            'technical_message': str(error_info.error),
            'should_retry': False,
            'fallback_data': None,
            'recovery_suggestion': '请检查并修正输入数据'
        }
    
    def _handle_network_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理网络错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '网络连接失败，请检查网络设置',
            'technical_message': str(error_info.error),
            'should_retry': True,
            'fallback_data': self._get_cached_data(error_info.context),
            'recovery_suggestion': '检查网络连接或稍后重试'
        }
    
    def _handle_configuration_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理配置错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '系统配置错误',
            'technical_message': str(error_info.error),
            'should_retry': False,
            'fallback_data': None,
            'recovery_suggestion': '检查系统配置文件'
        }
    
    def _handle_user_input_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理用户输入错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '输入参数无效',
            'technical_message': str(error_info.error),
            'should_retry': False,
            'fallback_data': None,
            'recovery_suggestion': '请检查输入参数的格式和范围'
        }
    
    def _handle_system_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理系统错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '系统内部错误',
            'technical_message': str(error_info.error),
            'should_retry': True,
            'fallback_data': None,
            'recovery_suggestion': '请稍后重试或联系管理员'
        }
    
    def _handle_generic_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """处理通用错误"""
        return {
            'success': False,
            'user_message': error_info.user_message or '发生未知错误',
            'technical_message': str(error_info.error),
            'should_retry': False,
            'fallback_data': None,
            'recovery_suggestion': '请联系技术支持'
        }
    
    def _get_cached_data(self, context: Dict[str, Any]) -> Any:
        """获取缓存数据作为后备"""
        try:
            # 尝试从上下文中获取缓存相关信息
            if 'symbol' in context:
                # ETF数据缓存恢复
                from etf_dashboard.data.cache import DataCache
                from etf_dashboard.config import get_config
                
                config = get_config()
                cache = DataCache(config.data.cache_dir)
                
                symbol = context['symbol']
                cached_data = cache.get_cached_data(symbol)
                
                if cached_data is not None:
                    self.logger.info(f"使用缓存数据作为后备: {symbol}")
                    return cached_data
            
            # 尝试获取默认数据
            if 'default_data' in context:
                return context['default_data']
                
        except Exception as e:
            self.logger.warning(f"获取缓存数据失败: {str(e)}")
        
        return None
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.error_history:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {},
                'recent_errors': []
            }
        
        # 按类别统计
        by_category = {}
        for error_info in self.error_history:
            category = error_info.category.value
            by_category[category] = by_category.get(category, 0) + 1
        
        # 按严重程度统计
        by_severity = {}
        for error_info in self.error_history:
            severity = error_info.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # 最近的错误
        recent_errors = [
            {
                'timestamp': error_info.timestamp.isoformat(),
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'message': error_info.user_message
            }
            for error_info in self.error_history[-10:]  # 最近10个错误
        ]
        
        return {
            'total_errors': len(self.error_history),
            'by_category': by_category,
            'by_severity': by_severity,
            'recent_errors': recent_errors
        }
    
    def clear_error_history(self):
        """清空错误历史"""
        self.error_history.clear()
        self.logger.info("错误历史已清空")


def error_handler(
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: str = None,
    recovery_suggestion: str = None,
    fallback_return: Any = None
):
    """
    错误处理装饰器
    
    Args:
        category: 错误类别
        severity: 错误严重程度
        user_message: 用户友好的错误消息
        recovery_suggestion: 恢复建议
        fallback_return: 发生错误时的返回值
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取全局错误处理器实例
                handler = GlobalErrorHandler()
                
                # 构建上下文信息
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args)[:200],  # 限制长度避免日志过长
                    'kwargs': str(kwargs)[:200]
                }
                
                # 处理错误
                result = handler.handle_error(
                    error=e,
                    category=category,
                    severity=severity,
                    context=context,
                    user_message=user_message,
                    recovery_suggestion=recovery_suggestion
                )
                
                # 根据处理结果决定返回值
                if result.get('fallback_data') is not None:
                    return result['fallback_data']
                elif fallback_return is not None:
                    return fallback_return
                else:
                    # 重新抛出异常，但附加处理信息
                    raise RuntimeError(result['user_message']) from e
        
        return wrapper
    return decorator


# 全局错误处理器实例
global_error_handler = GlobalErrorHandler()