"""
UI错误处理组件

为Streamlit界面提供用户友好的错误显示和处理功能。
包括错误提示、恢复建议、系统状态显示等UI组件。
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from .error_handler import ErrorCategory, ErrorSeverity, GlobalErrorHandler


class UIErrorDisplayMode(Enum):
    """UI错误显示模式"""
    MINIMAL = "minimal"      # 最小化显示，只显示用户消息
    STANDARD = "standard"    # 标准显示，包含恢复建议
    DETAILED = "detailed"    # 详细显示，包含技术信息
    DEBUG = "debug"          # 调试模式，显示所有信息


class UIErrorHandler:
    """UI错误处理器"""
    
    def __init__(self, error_handler: GlobalErrorHandler = None):
        """
        初始化UI错误处理器
        
        Args:
            error_handler: 全局错误处理器实例
        """
        self.error_handler = error_handler or GlobalErrorHandler()
        self.logger = logging.getLogger(__name__)
        
        # 错误显示配置
        self.display_mode = UIErrorDisplayMode.STANDARD
        self.show_technical_details = False
        self.auto_collapse_details = True
    
    def set_display_mode(self, mode: UIErrorDisplayMode):
        """设置错误显示模式"""
        self.display_mode = mode
        self.show_technical_details = mode in [UIErrorDisplayMode.DETAILED, UIErrorDisplayMode.DEBUG]
    
    def show_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Dict[str, Any] = None,
        user_message: str = None,
        recovery_suggestion: str = None,
        show_details: bool = None
    ) -> Dict[str, Any]:
        """
        在UI中显示错误信息
        
        Args:
            error: 异常对象
            category: 错误类别
            severity: 错误严重程度
            context: 错误上下文信息
            user_message: 用户友好的错误消息
            recovery_suggestion: 恢复建议
            show_details: 是否显示技术详情
            
        Returns:
            错误处理结果字典
        """
        # 处理错误
        result = self.error_handler.handle_error(
            error=error,
            category=category,
            severity=severity,
            context=context,
            user_message=user_message,
            recovery_suggestion=recovery_suggestion
        )
        
        # 在UI中显示错误
        self._display_error_in_ui(result, show_details)
        
        return result
    
    def _display_error_in_ui(self, error_result: Dict[str, Any], show_details: bool = None):
        """在UI中显示错误信息"""
        try:
            user_message = error_result.get('user_message', '发生未知错误')
            technical_message = error_result.get('technical_message', '')
            recovery_suggestion = error_result.get('recovery_suggestion', '')
            should_retry = error_result.get('should_retry', False)
            fallback_data = error_result.get('fallback_data')
            
            # 根据严重程度选择显示方式
            severity = error_result.get('severity', ErrorSeverity.MEDIUM)
            
            if severity == ErrorSeverity.CRITICAL:
                st.error(f"🚨 严重错误: {user_message}")
            elif severity == ErrorSeverity.HIGH:
                st.error(f"❌ 错误: {user_message}")
            elif severity == ErrorSeverity.MEDIUM:
                st.warning(f"⚠️ 警告: {user_message}")
            else:
                st.info(f"ℹ️ 提示: {user_message}")
            
            # 显示恢复建议
            if recovery_suggestion and self.display_mode != UIErrorDisplayMode.MINIMAL:
                st.info(f"💡 建议: {recovery_suggestion}")
            
            # 显示重试选项
            if should_retry:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔄 重试", key=f"retry_{hash(user_message)}"):
                        st.rerun()
                with col2:
                    st.text("点击重试按钮重新执行操作")
            
            # 显示后备数据提示
            if fallback_data is not None:
                st.info("📦 正在使用缓存数据，可能不是最新信息")
            
            # 显示技术详情
            if show_details or (show_details is None and self.show_technical_details):
                with st.expander("🔧 技术详情", expanded=not self.auto_collapse_details):
                    if technical_message:
                        st.code(technical_message, language="text")
                    
                    # 显示错误统计
                    error_stats = self.error_handler.get_error_statistics()
                    if error_stats['total_errors'] > 0:
                        st.markdown("**错误统计:**")
                        st.json({
                            "总错误数": error_stats['total_errors'],
                            "按类别": error_stats['by_category'],
                            "按严重程度": error_stats['by_severity']
                        })
            
        except Exception as display_error:
            # 错误显示本身出错，使用最基本的显示方式
            st.error(f"显示错误信息失败: {str(display_error)}")
            st.error(f"原始错误: {error_result.get('user_message', '未知错误')}")
    
    def show_system_health(self, health_status: Dict[str, Any]):
        """显示系统健康状态"""
        try:
            overall_status = health_status.get('overall_status', 'unknown')
            
            # 显示整体状态
            if overall_status == 'healthy':
                st.success("🟢 系统状态: 健康")
            elif overall_status == 'degraded':
                st.warning("🟡 系统状态: 降级运行")
            else:
                st.error("🔴 系统状态: 异常")
            
            # 显示组件状态
            components = health_status.get('components', {})
            if components:
                st.subheader("组件状态")
                
                for name, component_health in components.items():
                    status = component_health.get('status', 'unknown')
                    message = component_health.get('message', '无详细信息')
                    
                    display_name = self._get_component_display_name(name)
                    
                    if status == 'healthy':
                        st.success(f"✅ {display_name}: {message}")
                    elif status == 'error':
                        st.error(f"❌ {display_name}: {message}")
                    else:
                        st.warning(f"⚠️ {display_name}: {message}")
            
            # 显示问题列表
            issues = health_status.get('issues', [])
            if issues:
                st.subheader("发现的问题")
                for issue in issues:
                    st.error(f"• {issue}")
            
            # 显示检查时间
            timestamp = health_status.get('timestamp')
            if timestamp:
                st.info(f"检查时间: {timestamp}")
                
        except Exception as e:
            st.error(f"显示系统健康状态失败: {str(e)}")
    
    def show_error_statistics(self):
        """显示错误统计信息"""
        try:
            stats = self.error_handler.get_error_statistics()
            
            if stats['total_errors'] == 0:
                st.success("🎉 暂无错误记录")
                return
            
            # 显示总体统计
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总错误数", stats['total_errors'])
            
            with col2:
                most_common_category = max(stats['by_category'].items(), key=lambda x: x[1])[0] if stats['by_category'] else "无"
                st.metric("最常见类别", most_common_category)
            
            with col3:
                most_common_severity = max(stats['by_severity'].items(), key=lambda x: x[1])[0] if stats['by_severity'] else "无"
                st.metric("最常见严重程度", most_common_severity)
            
            # 显示分类统计
            if stats['by_category']:
                st.subheader("按类别统计")
                category_data = []
                for category, count in stats['by_category'].items():
                    category_data.append({
                        "类别": self._get_category_display_name(category),
                        "数量": count,
                        "占比": f"{count / stats['total_errors'] * 100:.1f}%"
                    })
                
                st.dataframe(category_data, use_container_width=True, hide_index=True)
            
            # 显示最近错误
            if stats['recent_errors']:
                st.subheader("最近错误")
                for error_info in stats['recent_errors'][-5:]:  # 显示最近5个错误
                    timestamp = error_info['timestamp']
                    category = error_info['category']
                    severity = error_info['severity']
                    message = error_info['message']
                    
                    severity_icon = self._get_severity_icon(severity)
                    category_name = self._get_category_display_name(category)
                    
                    st.text(f"{severity_icon} [{timestamp}] {category_name}: {message}")
            
            # 清空错误历史按钮
            if st.button("🗑️ 清空错误历史"):
                self.error_handler.clear_error_history()
                st.success("错误历史已清空")
                st.rerun()
                
        except Exception as e:
            st.error(f"显示错误统计失败: {str(e)}")
    
    def create_error_recovery_panel(self, error_result: Dict[str, Any]):
        """创建错误恢复面板"""
        try:
            st.subheader("🔧 错误恢复")
            
            recovery_suggestion = error_result.get('recovery_suggestion', '')
            should_retry = error_result.get('should_retry', False)
            fallback_data = error_result.get('fallback_data')
            
            # 恢复选项
            recovery_options = []
            
            if should_retry:
                recovery_options.append("重试操作")
            
            if fallback_data is not None:
                recovery_options.append("使用缓存数据")
            
            if recovery_suggestion:
                recovery_options.append("按建议操作")
            
            recovery_options.append("联系技术支持")
            
            selected_option = st.selectbox(
                "选择恢复方式",
                options=recovery_options,
                help="选择适合的错误恢复方式"
            )
            
            # 根据选择显示相应的操作
            if selected_option == "重试操作":
                if st.button("🔄 立即重试", type="primary"):
                    st.rerun()
            
            elif selected_option == "使用缓存数据":
                st.info("系统将尝试使用本地缓存的数据继续运行")
                if st.button("📦 使用缓存数据"):
                    # 这里可以设置一个标志，让应用使用缓存数据
                    st.session_state['use_fallback_data'] = True
                    st.rerun()
            
            elif selected_option == "按建议操作":
                st.info(f"建议操作: {recovery_suggestion}")
                st.markdown("请按照上述建议进行操作，然后重试")
            
            elif selected_option == "联系技术支持":
                st.info("请将以下信息提供给技术支持:")
                
                support_info = {
                    "错误时间": datetime.now().isoformat(),
                    "错误消息": error_result.get('user_message', ''),
                    "技术详情": error_result.get('technical_message', ''),
                    "系统信息": {
                        "Python版本": "3.x",
                        "Streamlit版本": st.__version__
                    }
                }
                
                st.json(support_info)
                
                if st.button("📋 复制支持信息"):
                    # 这里可以实现复制到剪贴板的功能
                    st.success("支持信息已准备好，请手动复制上述JSON内容")
                    
        except Exception as e:
            st.error(f"创建错误恢复面板失败: {str(e)}")
    
    def _get_component_display_name(self, component_name: str) -> str:
        """获取组件显示名称"""
        name_mapping = {
            'data_loader': '数据加载器',
            'technical_indicators': '技术指标计算器',
            'signal_manager': '信号管理器',
            'portfolio_manager': '组合管理器',
            'error_handler': '错误处理器'
        }
        return name_mapping.get(component_name, component_name)
    
    def _get_category_display_name(self, category: str) -> str:
        """获取错误类别显示名称"""
        category_mapping = {
            'data_access': '数据访问',
            'calculation': '计算处理',
            'validation': '数据验证',
            'network': '网络连接',
            'configuration': '配置错误',
            'user_input': '用户输入',
            'system': '系统错误'
        }
        return category_mapping.get(category, category)
    
    def _get_severity_icon(self, severity: str) -> str:
        """获取严重程度图标"""
        icon_mapping = {
            'low': 'ℹ️',
            'medium': '⚠️',
            'high': '❌',
            'critical': '🚨'
        }
        return icon_mapping.get(severity, '❓')


# 全局UI错误处理器实例
ui_error_handler = UIErrorHandler()


def show_error_with_recovery(
    error: Exception,
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Dict[str, Any] = None,
    user_message: str = None,
    recovery_suggestion: str = None
) -> Dict[str, Any]:
    """
    显示错误并提供恢复选项的便捷函数
    
    Args:
        error: 异常对象
        category: 错误类别
        severity: 错误严重程度
        context: 错误上下文信息
        user_message: 用户友好的错误消息
        recovery_suggestion: 恢复建议
        
    Returns:
        错误处理结果字典
    """
    return ui_error_handler.show_error(
        error=error,
        category=category,
        severity=severity,
        context=context,
        user_message=user_message,
        recovery_suggestion=recovery_suggestion
    )


def create_error_boundary(func):
    """
    创建错误边界装饰器，用于包装Streamlit页面函数
    
    Args:
        func: 要包装的函数
        
    Returns:
        包装后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 显示用户友好的错误信息
            ui_error_handler.show_error(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={'function': func.__name__},
                user_message=f"页面 {func.__name__} 加载失败",
                recovery_suggestion="请刷新页面或联系技术支持"
            )
            
            # 创建错误恢复面板
            error_result = {
                'user_message': f"页面 {func.__name__} 加载失败",
                'technical_message': str(e),
                'recovery_suggestion': "请刷新页面或联系技术支持",
                'should_retry': True,
                'fallback_data': None
            }
            ui_error_handler.create_error_recovery_panel(error_result)
    
    return wrapper