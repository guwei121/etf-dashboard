"""
核心模块

包含系统核心功能，如错误处理、数据流管理和模块集成等。
"""

from .error_handler import GlobalErrorHandler
from .integration import SystemIntegrator
from .data_flow import DataFlowManager

__all__ = ['GlobalErrorHandler', 'SystemIntegrator', 'DataFlowManager']