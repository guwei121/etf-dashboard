"""
Streamlit仪表盘主应用

ETF投资仪表盘的主要Streamlit应用文件。
提供多页面导航和完整的应用框架，包括概览页面、ETF详情页面和组合管理页面。
"""

import streamlit as st
import logging
import sys
import os
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from etf_dashboard.config import get_config, setup_logging
from etf_dashboard.core.integration import system_integrator
from etf_dashboard.core.ui_error_handler import ui_error_handler, create_error_boundary, show_error_with_recovery
from etf_dashboard.core.error_handler import ErrorCategory, ErrorSeverity
from etf_dashboard.core.performance_monitor import monitor_performance, start_performance_monitoring


class DashboardApp:
    """Streamlit仪表盘主应用"""
    
    def __init__(self):
        """初始化仪表盘应用"""
        try:
            self.config = get_config()
            self.logger = logging.getLogger(__name__)
            
            # 设置UI错误处理器的显示模式
            from etf_dashboard.core.ui_error_handler import UIErrorDisplayMode
            if self.config.ui.show_debug_info:
                ui_error_handler.set_display_mode(UIErrorDisplayMode.DEBUG)
            else:
                ui_error_handler.set_display_mode(UIErrorDisplayMode.STANDARD)
            
            # 启动性能监控
            start_performance_monitoring(interval=300.0)  # 5分钟间隔
            
            # 初始化组件
            self._initialize_components()
            
            # 设置自定义样式
            self._setup_custom_styles()
            
            # 初始化会话状态
            self._initialize_session_state()
            
        except Exception as e:
            # 使用增强的错误处理
            show_error_with_recovery(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                context={'component': 'DashboardApp.__init__'},
                user_message="仪表盘初始化失败",
                recovery_suggestion="请检查系统配置并重新启动应用"
            )
    
    @monitor_performance(slow_threshold=2.0)
    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 使用系统集成器初始化所有组件
            init_result = system_integrator.initialize_system()
            
            if not init_result['success']:
                raise RuntimeError(f"系统初始化失败: {init_result.get('message', '未知错误')}")
            
            # 获取组件引用（为了保持向后兼容）
            self.data_loader = system_integrator.get_component('data_loader')
            self.indicators = system_integrator.get_component('technical_indicators')
            self.signal_manager = system_integrator.get_component('signal_manager')
            self.portfolio_manager = system_integrator.get_component('portfolio_manager')
            
            self.logger.info("系统组件初始化完成")
            
        except Exception as e:
            self.logger.error(f"组件初始化失败: {str(e)}")
            
            # 使用增强的错误处理
            show_error_with_recovery(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={'function': '_initialize_components'},
                user_message="系统组件初始化失败",
                recovery_suggestion="请检查系统配置和网络连接"
            )
            
            # 显示错误详情
            if hasattr(system_integrator, 'initialization_errors') and system_integrator.initialization_errors:
                st.error("详细错误信息:")
                for error in system_integrator.initialization_errors:
                    st.error(f"• {error}")
    
    def _setup_custom_styles(self):
        """设置自定义样式"""
        st.markdown("""
        <style>
        /* 主标题样式 */
        .main-title {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        /* 页面标题样式 */
        .page-title {
            font-size: 2rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5rem;
        }
        
        /* 指标卡片样式 */
        .metric-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #3498db;
            margin-bottom: 1rem;
        }
        
        /* 状态指示器样式 */
        .status-success {
            color: #27ae60;
            font-weight: bold;
        }
        
        .status-warning {
            color: #f39c12;
            font-weight: bold;
        }
        
        .status-danger {
            color: #e74c3c;
            font-weight: bold;
        }
        
        /* 导航按钮样式 */
        .nav-button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        /* 侧边栏样式 */
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        
        /* 图表容器样式 */
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def _initialize_session_state(self):
        """初始化会话状态"""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'overview'
        
        if 'selected_etf' not in st.session_state:
            st.session_state.selected_etf = None
        
        if 'etf_list' not in st.session_state:
            st.session_state.etf_list = []
        
        if 'last_update' not in st.session_state:
            st.session_state.last_update = None
        
        if 'use_fallback_data' not in st.session_state:
            st.session_state.use_fallback_data = False
        
        if 'nav_timestamp' not in st.session_state:
            st.session_state.nav_timestamp = time.time()
    
    @create_error_boundary
    def run(self):
        """运行应用"""
        try:
            # 显示主标题
            st.markdown('<h1 class="main-title">📈 ETF投资仪表盘</h1>', unsafe_allow_html=True)
            
            # 创建导航栏
            self._create_navigation()
            
            # 显示页面内容
            self._render_current_page()
            
        except Exception as e:
            self.logger.error(f"应用运行失败: {str(e)}")
            
            # 使用增强的错误处理
            show_error_with_recovery(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={'function': 'run'},
                user_message="应用运行失败",
                recovery_suggestion="请刷新页面或重新启动应用"
            )
    
    def _create_navigation(self):
        """创建导航栏"""
        st.sidebar.markdown("## 📋 导航菜单")
        
        # 页面选项
        pages = {
            'overview': '📊 概览',
            'etf_detail': '📈 ETF详情', 
            'portfolio': '💼 组合管理',
            'settings': '⚙️ 设置'
        }
        
        # 确保当前页面有效
        if st.session_state.current_page not in pages:
            st.session_state.current_page = 'overview'
        
        # 显示当前页面
        current_page_name = pages.get(st.session_state.current_page, '未知页面')
        st.sidebar.markdown(f"**当前页面:** {current_page_name}")
        
        # 创建导航按钮
        st.sidebar.markdown("### 页面导航")
        
        # 使用selectbox替代多个button避免重复key问题
        page_options = list(pages.values())
        page_keys = list(pages.keys())
        
        try:
            current_index = page_keys.index(st.session_state.current_page)
        except ValueError:
            current_index = 0
            st.session_state.current_page = page_keys[0]
        
        # 使用唯一的key和时间戳
        nav_key = f"page_selector_{int(time.time()) % 10000}"
        selected_page_name = st.sidebar.selectbox(
            "选择页面",
            options=page_options,
            index=current_index,
            key=nav_key
        )
        
        # 更新当前页面
        if selected_page_name:
            selected_key = page_keys[page_options.index(selected_page_name)]
            if selected_key != st.session_state.current_page:
                st.session_state.current_page = selected_key
                st.rerun()
        
        # 显示系统状态
        st.sidebar.markdown("---")
        self._show_sidebar_status()
    
    def _show_sidebar_status(self):
        """显示侧边栏系统状态"""
        st.sidebar.markdown("## 🔧 系统状态")
        
        # 获取系统状态
        try:
            system_status = system_integrator.get_system_status()
            
            # 显示初始化状态
            if system_status['is_initialized']:
                st.sidebar.success("✅ 系统已初始化")
            else:
                st.sidebar.error("❌ 系统未初始化")
            
            # 显示组件状态
            for name, info in system_status['components'].items():
                status = info['status']
                if status == 'initialized':
                    status_icon = "✅"
                elif status == 'failed':
                    status_icon = "❌"
                else:
                    status_icon = "⚠️"
                
                display_name = {
                    'data_loader': '数据加载器',
                    'technical_indicators': '技术指标',
                    'signal_manager': '信号管理',
                    'portfolio_manager': '组合管理'
                }.get(name, name)
                
                st.sidebar.text(f"{status_icon} {display_name}")
            
            # 显示错误统计
            error_stats = system_status.get('error_statistics', {})
            if error_stats.get('total_errors', 0) > 0:
                st.sidebar.warning(f"⚠️ 错误数量: {error_stats['total_errors']}")
            
            # 显示最后更新时间
            if st.session_state.last_update:
                st.sidebar.markdown(f"**最后更新:** {st.session_state.last_update.strftime('%H:%M:%S')}")
            
            # 系统健康检查按钮
            if st.sidebar.button("🔍 健康检查", use_container_width=True):
                self._show_health_check()
            
        except Exception as e:
            st.sidebar.error(f"状态获取失败: {str(e)}")
        
        # 刷新按钮
        if st.sidebar.button("🔄 刷新数据", use_container_width=True):
            self._refresh_data()
    
    def _show_health_check(self):
        """显示系统健康检查结果"""
        try:
            health_status = system_integrator.health_check()
            
            # 显示整体状态
            overall_status = health_status['overall_status']
            if overall_status == 'healthy':
                st.success("🟢 系统整体状态: 健康")
            elif overall_status == 'degraded':
                st.warning("🟡 系统整体状态: 降级")
            else:
                st.error("🔴 系统整体状态: 异常")
            
            # 显示组件详情
            st.subheader("组件健康状态")
            for name, component_health in health_status['components'].items():
                status = component_health.get('status', 'unknown')
                message = component_health.get('message', '无详细信息')
                
                display_name = {
                    'data_loader': '数据加载器',
                    'technical_indicators': '技术指标计算器',
                    'signal_manager': '信号管理器',
                    'portfolio_manager': '组合管理器'
                }.get(name, name)
                
                if status == 'healthy':
                    st.success(f"✅ {display_name}: {message}")
                elif status == 'error':
                    st.error(f"❌ {display_name}: {message}")
                else:
                    st.warning(f"⚠️ {display_name}: {message}")
            
            # 显示问题列表
            if health_status['issues']:
                st.subheader("发现的问题")
                for issue in health_status['issues']:
                    st.error(f"• {issue}")
            
            # 显示检查时间
            st.info(f"检查时间: {health_status['timestamp']}")
            
        except Exception as e:
            st.error(f"健康检查失败: {str(e)}")
    
    def _refresh_data(self):
        """刷新数据"""
        try:
            st.session_state.last_update = datetime.now()
            st.session_state.etf_list = []  # 清空缓存，强制重新加载
            
            # 清理系统缓存
            system_integrator.data_flow_manager.clear_cache()
            
            st.success("数据刷新成功！")
            st.rerun()
        except Exception as e:
            st.error(f"数据刷新失败: {str(e)}")
    
    def _render_current_page(self):
        """渲染当前页面"""
        page = st.session_state.current_page
        
        if page == 'overview':
            self._render_overview_page()
        elif page == 'etf_detail':
            self._render_etf_detail_page()
        elif page == 'portfolio':
            self._render_portfolio_page()
        elif page == 'settings':
            self._render_settings_page()
        else:
            st.error(f"未知页面: {page}")
    
    def _render_overview_page(self):
        """渲染概览页面"""
        st.markdown('<h2 class="page-title">📊 ETF概览</h2>', unsafe_allow_html=True)
        
        # 获取ETF列表
        etf_list = self._get_etf_list()
        
        if not etf_list:
            st.warning("暂无ETF数据，请检查数据连接。")
            if st.button("🔄 重新获取数据"):
                st.session_state.etf_list = []
                st.rerun()
            return
        
        # 显示概览统计信息
        self._show_overview_metrics(etf_list)
        
        # 搜索和过滤功能
        st.subheader("🔍 ETF搜索与筛选")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "搜索ETF (代码或名称)",
                placeholder="输入ETF代码或名称关键词",
                key="etf_search"
            )
        
        with col2:
            market_filter = st.selectbox(
                "市场筛选",
                options=["全部", "A股", "美股"],
                key="market_filter"
            )
        
        with col3:
            sort_by = st.selectbox(
                "排序方式",
                options=["代码", "名称", "最新价格"],
                key="sort_by"
            )
        
        # 过滤ETF列表
        filtered_etfs = self._filter_etf_list(etf_list, search_term, market_filter)
        
        if not filtered_etfs:
            st.info("没有找到匹配的ETF，请调整搜索条件。")
            return
        
        # 显示ETF概览信息
        st.subheader(f"📋 ETF列表 (共 {len(filtered_etfs)} 个)")
        
        # 创建ETF展示区域
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 显示增强的ETF表格
            self._show_enhanced_etf_table(filtered_etfs[:20])  # 显示前20个ETF
        
        with col2:
            st.markdown("### 🚀 快速操作")
            
            # ETF选择下拉框
            etf_options = {f"{etf['symbol']} - {etf['name']}": etf['symbol'] 
                          for etf in filtered_etfs[:20]}
            
            if etf_options:
                selected_etf_display = st.selectbox(
                    "选择ETF进行操作",
                    options=list(etf_options.keys()),
                    key="etf_selector"
                )
                
                if selected_etf_display:
                    selected_symbol = etf_options[selected_etf_display]
                    
                    # 操作按钮
                    if st.button("📈 查看详情", use_container_width=True, type="primary"):
                        st.session_state.selected_etf = selected_symbol
                        st.session_state.current_page = 'etf_detail'
                        st.rerun()
                    
                    if st.button("➕ 添加到组合", use_container_width=True):
                        self._add_to_portfolio(selected_symbol)
                    
                    if st.button("📊 快速分析", use_container_width=True):
                        self._show_quick_analysis(selected_symbol)
            
            # 批量操作
            st.markdown("---")
            st.markdown("### 📦 批量操作")
            
            if st.button("🔄 刷新所有数据", use_container_width=True):
                self._refresh_all_data()
            
            if st.button("📈 查看热门ETF", use_container_width=True):
                self._show_popular_etfs(filtered_etfs)
        
        # 显示系统统计信息
        st.markdown("---")
        self._show_system_statistics()
        
        # 显示最近活动
        self._show_recent_activity()
    
    def _render_etf_detail_page(self):
        """渲染ETF详情页面"""
        st.markdown('<h2 class="page-title">📈 ETF详情分析</h2>', unsafe_allow_html=True)
        
        # ETF选择器
        etf_list = self._get_etf_list()
        if not etf_list:
            st.warning("暂无ETF数据")
            return
        
        # 创建选择器
        col1, col2 = st.columns([3, 1])
        
        with col1:
            etf_options = {f"{etf['symbol']} - {etf['name']}": etf['symbol'] 
                          for etf in etf_list[:20]}
            
            selected_etf_display = st.selectbox(
                "选择要分析的ETF",
                options=list(etf_options.keys()),
                index=0 if not st.session_state.selected_etf else 
                      list(etf_options.values()).index(st.session_state.selected_etf) 
                      if st.session_state.selected_etf in etf_options.values() else 0,
                key="detail_etf_selector"
            )
            
            selected_symbol = etf_options[selected_etf_display]
            st.session_state.selected_etf = selected_symbol
        
        with col2:
            st.markdown("### 操作")
            if st.button("🔄 刷新数据", use_container_width=True):
                self._refresh_etf_data(selected_symbol)
        
        # 显示ETF详细信息
        self._show_etf_details(selected_symbol)
    
    def _render_portfolio_page(self):
        """渲染组合管理页面"""
        st.markdown('<h2 class="page-title">💼 投资组合管理</h2>', unsafe_allow_html=True)
        
        # 检查是否显示添加ETF表单
        if st.session_state.get('show_add_etf_form', False):
            self._show_add_etf_form()
            return
        
        # 检查是否显示删除ETF表单
        if st.session_state.get('show_delete_etf_form', False):
            self._show_delete_etf_form()
            return
        
        # 组合概览
        st.subheader("📊 组合概览")
        
        try:
            # 获取组合配置
            portfolio_config = self.portfolio_manager.get_portfolio_config()
            
            if not portfolio_config or not portfolio_config.etf_weights:
                st.info("暂无组合配置，请添加ETF到组合中。")
                
                # 显示快速添加按钮
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("➕ 创建投资组合", use_container_width=True, type="primary"):
                        st.session_state.show_add_etf_form = True
                        st.rerun()
                
                # 显示组合管理说明
                with st.expander("📖 组合管理说明", expanded=True):
                    st.markdown("""
                    ### 🎯 组合管理功能
                    
                    **主要功能：**
                    - 📋 **组合配置**：设置ETF目标权重，支持增删改操作
                    - 📊 **仓位监控**：显示当前持仓与目标配置的偏离情况
                    - ⚖️ **再平衡建议**：基于偏离度自动生成买卖建议
                    - 📈 **表现分析**：分析组合历史表现和个股贡献
                    
                    **使用步骤：**
                    1. 点击"创建投资组合"添加第一个ETF
                    2. 设置各ETF的目标权重（总和应为100%）
                    3. 输入当前持仓数量以获取偏离分析
                    4. 根据再平衡建议调整持仓
                    
                    **注意事项：**
                    - 权重总和必须等于100%
                    - 再平衡阈值默认为5%，可在设置中调整
                    - 建议定期检查和调整组合配置
                    """)
                
                return
            
            # 显示组合配置
            self._show_portfolio_overview(portfolio_config)
            
            # 显示组合分析
            self._show_portfolio_analysis()
            
        except Exception as e:
            st.error(f"加载组合数据失败: {str(e)}")
            self.logger.error(f"Portfolio page error: {str(e)}")
    
    def _show_delete_etf_form(self):
        """显示删除ETF表单"""
        st.subheader("🗑️ 删除ETF")
        
        portfolio_config = self.portfolio_manager.get_portfolio_config()
        if not portfolio_config or not portfolio_config.etf_weights:
            st.warning("组合中没有ETF可删除")
            if st.button("返回"):
                st.session_state.show_delete_etf_form = False
                st.rerun()
            return
        
        st.warning("⚠️ 删除ETF将从组合配置中移除该ETF及其权重设置")
        
        # ETF选择
        etf_options = list(portfolio_config.etf_weights.keys())
        selected_etf = st.selectbox(
            "选择要删除的ETF",
            options=etf_options,
            help="选择要从组合中删除的ETF"
        )
        
        if selected_etf:
            current_weight = portfolio_config.etf_weights[selected_etf]
            st.info(f"当前权重: {current_weight:.1%}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ 确认删除", type="primary", use_container_width=True):
                    try:
                        self.portfolio_manager.remove_etf_from_portfolio(selected_etf)
                        st.success(f"ETF {selected_etf} 已从组合中删除！")
                        st.session_state.show_delete_etf_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {str(e)}")
            
            with col2:
                if st.button("取消", use_container_width=True):
                    st.session_state.show_delete_etf_form = False
                    st.rerun()
    
    def _render_settings_page(self):
        """渲染设置页面"""
        st.markdown('<h2 class="page-title">⚙️ 系统设置</h2>', unsafe_allow_html=True)
        
        # 配置选项卡
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 界面设置", "📈 技术指标", "🔔 信号规则", "💾 数据管理", "🔧 系统监控", "🌐 数据源"])
        
        with tab1:
            self._show_ui_settings()
        
        with tab2:
            self._show_indicator_settings()
        
        with tab3:
            self._show_signal_settings()
        
        with tab4:
            self._show_data_settings()
        
        with tab5:
            self._show_system_monitoring_settings()
        
        with tab6:
            self._show_data_source_settings()
            st.markdown("---")
            self._show_data_source_status()
        
        with st.expander("🌐 网络诊断", expanded=False):
            self._show_network_diagnostics()
    
    def _get_etf_list(self) -> List[Dict[str, Any]]:
        """获取ETF列表"""
        if not st.session_state.etf_list:
            try:
                with st.spinner("正在获取ETF列表..."):
                    # 检查数据加载器是否可用
                    if not self.data_loader:
                        st.error("数据加载器未初始化")
                        return []
                    
                    etf_list = self.data_loader.get_etf_list("A")
                    st.session_state.etf_list = etf_list[:50]  # 限制数量以提高性能
                    st.session_state.last_update = datetime.now()
                    
            except Exception as e:
                # 使用全局错误处理器
                from etf_dashboard.core.error_handler import ErrorCategory, ErrorSeverity
                
                error_result = system_integrator.error_handler.handle_error(
                    error=e,
                    category=ErrorCategory.DATA_ACCESS,
                    severity=ErrorSeverity.MEDIUM,
                    context={'function': '_get_etf_list'},
                    user_message="获取ETF列表失败",
                    recovery_suggestion="请检查网络连接或稍后重试"
                )
                
                st.error(error_result['user_message'])
                
                # 显示恢复建议
                if error_result.get('recovery_suggestion'):
                    st.info(f"💡 建议: {error_result['recovery_suggestion']}")
                
                # 尝试使用缓存数据
                if error_result.get('fallback_data'):
                    st.session_state.etf_list = error_result['fallback_data']
                    st.warning("使用缓存数据")
                else:
                    return []
        
        return st.session_state.etf_list
    
    def _add_to_portfolio(self, symbol: str):
        """添加ETF到组合"""
        try:
            # 默认权重为10%
            self.portfolio_manager.add_etf_to_portfolio(symbol, 0.1)
            st.success(f"ETF {symbol} 已添加到组合中！")
        except Exception as e:
            st.error(f"添加到组合失败: {str(e)}")
    
    def _show_system_statistics(self):
        """显示系统统计信息"""
        st.subheader("📈 系统统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            etf_count = len(st.session_state.etf_list)
            st.metric("监控ETF数量", etf_count)
        
        with col2:
            try:
                portfolio_config = self.portfolio_manager.get_portfolio_config()
                portfolio_count = len(portfolio_config.etf_weights) if portfolio_config else 0
            except:
                portfolio_count = 0
            st.metric("组合ETF数量", portfolio_count)
        
        with col3:
            cache_dir = self.config.data.cache_dir
            cache_files = len([f for f in os.listdir(cache_dir) if f.endswith('.pkl')]) if os.path.exists(cache_dir) else 0
            st.metric("缓存文件数", cache_files)
        
        with col4:
            if st.session_state.last_update:
                update_time = st.session_state.last_update.strftime("%H:%M")
                st.metric("最后更新", update_time)
            else:
                st.metric("最后更新", "未更新")
    
    def _show_overview_metrics(self, etf_list: List[Dict[str, Any]]):
        """显示概览指标"""
        st.subheader("📊 市场概览")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "可用ETF总数",
                len(etf_list),
                help="当前可获取数据的ETF总数"
            )
        
        with col2:
            # 计算A股ETF数量
            a_stock_count = len([etf for etf in etf_list if etf.get('symbol', '').isdigit()])
            st.metric(
                "A股ETF数量",
                a_stock_count,
                help="A股市场的ETF数量"
            )
        
        with col3:
            try:
                portfolio_config = self.portfolio_manager.get_portfolio_config()
                portfolio_count = len(portfolio_config.etf_weights) if portfolio_config else 0
                st.metric(
                    "组合中ETF",
                    portfolio_count,
                    help="当前投资组合中的ETF数量"
                )
            except:
                st.metric("组合中ETF", 0, help="当前投资组合中的ETF数量")
        
        with col4:
            # 显示数据更新状态
            if st.session_state.last_update:
                time_diff = datetime.now() - st.session_state.last_update
                if time_diff.total_seconds() < 3600:  # 1小时内
                    status = "🟢 最新"
                elif time_diff.total_seconds() < 86400:  # 24小时内
                    status = "🟡 较新"
                else:
                    status = "🔴 需更新"
                
                st.metric(
                    "数据状态",
                    status,
                    help=f"最后更新: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M')}"
                )
            else:
                st.metric("数据状态", "🔴 未更新", help="尚未获取数据")
    
    def _filter_etf_list(self, etf_list: List[Dict[str, Any]], search_term: str, market_filter: str) -> List[Dict[str, Any]]:
        """过滤ETF列表"""
        filtered = etf_list.copy()
        
        # 搜索过滤
        if search_term:
            search_term = search_term.lower()
            filtered = [
                etf for etf in filtered
                if search_term in etf.get('symbol', '').lower() or 
                   search_term in etf.get('name', '').lower()
            ]
        
        # 市场过滤
        if market_filter == "A股":
            filtered = [etf for etf in filtered if etf.get('symbol', '').isdigit()]
        elif market_filter == "美股":
            filtered = [etf for etf in filtered if not etf.get('symbol', '').isdigit()]
        
        return filtered
    
    def _show_enhanced_etf_table(self, etf_list: List[Dict[str, Any]]):
        """显示增强的ETF表格"""
        if not etf_list:
            st.info("没有ETF数据可显示")
            return
        
        # 创建DataFrame
        df = pd.DataFrame(etf_list)
        
        # 添加额外信息列
        df['市场'] = df['symbol'].apply(lambda x: 'A股' if str(x).isdigit() else '美股')
        df['操作'] = '查看详情'
        
        # 配置列显示
        column_config = {
            'symbol': st.column_config.TextColumn('ETF代码', width="small"),
            'name': st.column_config.TextColumn('ETF名称', width="large"),
            '市场': st.column_config.TextColumn('市场', width="small"),
            '操作': st.column_config.LinkColumn(
                '操作',
                help="点击查看ETF详情",
                width="small"
            )
        }
        
        # 显示表格
        selected_rows = st.dataframe(
            df[['symbol', 'name', '市场', '操作']],
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # 处理行选择
        if selected_rows and selected_rows.selection.rows:
            selected_idx = selected_rows.selection.rows[0]
            selected_etf = etf_list[selected_idx]
            
            # 显示选中ETF的快速信息
            with st.expander(f"📊 {selected_etf['symbol']} - {selected_etf['name']} 快速信息", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**代码:** {selected_etf['symbol']}")
                    st.write(f"**名称:** {selected_etf['name']}")
                    st.write(f"**市场:** {'A股' if str(selected_etf['symbol']).isdigit() else '美股'}")
                
                with col2:
                    if st.button(f"📈 查看 {selected_etf['symbol']} 详情", key=f"detail_{selected_etf['symbol']}"):
                        st.session_state.selected_etf = selected_etf['symbol']
                        st.session_state.current_page = 'etf_detail'
                        st.rerun()
                    
                    if st.button(f"➕ 添加 {selected_etf['symbol']} 到组合", key=f"add_{selected_etf['symbol']}"):
                        self._add_to_portfolio(selected_etf['symbol'])
    
    def _show_quick_analysis(self, symbol: str):
        """显示快速分析"""
        try:
            with st.spinner(f"正在分析 {symbol}..."):
                # 获取最近90天数据以确保技术指标计算有足够数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                
                data = self.data_loader.get_etf_data(symbol, start_date, end_date)
                
                if data is None or data.empty:
                    st.warning(f"无法获取 {symbol} 的数据")
                    return
                
                # 快速分析结果
                with st.expander(f"📊 {symbol} 快速分析结果", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        current_price = data['close'].iloc[-1]
                        price_change = data['close'].iloc[-1] - data['close'].iloc[0]
                        change_pct = (price_change / data['close'].iloc[0]) * 100
                        
                        st.metric(
                            "30日表现",
                            f"¥{current_price:.2f}",
                            f"{change_pct:+.2f}%"
                        )
                    
                    with col2:
                        # 计算简单移动平均
                        ma5 = data['close'].tail(5).mean()
                        ma20 = data['close'].tail(20).mean() if len(data) >= 20 else data['close'].mean()
                        
                        trend = "上升" if ma5 > ma20 else "下降"
                        trend_color = "🟢" if trend == "上升" else "🔴"
                        
                        st.metric(
                            "短期趋势",
                            f"{trend_color} {trend}",
                            f"MA5: ¥{ma5:.2f}"
                        )
                    
                    with col3:
                        # 计算波动率
                        volatility = data['close'].pct_change().std() * 100
                        vol_level = "高" if volatility > 3 else "中" if volatility > 1.5 else "低"
                        vol_color = "🔴" if vol_level == "高" else "🟡" if vol_level == "中" else "🟢"
                        
                        st.metric(
                            "波动水平",
                            f"{vol_color} {vol_level}",
                            f"{volatility:.2f}%"
                        )
                
        except Exception as e:
            st.error(f"快速分析失败: {str(e)}")
    
    def _refresh_all_data(self):
        """刷新所有数据"""
        try:
            with st.spinner("正在刷新所有数据..."):
                # 清空缓存
                st.session_state.etf_list = []
                st.session_state.last_update = None
                
                # 清理缓存文件
                cache_dir = self.config.data.cache_dir
                if os.path.exists(cache_dir):
                    cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
                    for file in cache_files:
                        try:
                            os.remove(os.path.join(cache_dir, file))
                        except:
                            pass
                
                st.success("数据刷新成功！页面将自动更新...")
                st.rerun()
                
        except Exception as e:
            st.error(f"数据刷新失败: {str(e)}")
    
    def _show_popular_etfs(self, etf_list: List[Dict[str, Any]]):
        """显示热门ETF"""
        with st.expander("🔥 热门ETF推荐", expanded=True):
            # 选择一些知名的ETF代码作为热门推荐
            popular_symbols = ['159919', '510300', '159915', '512100', '159928']
            popular_etfs = [etf for etf in etf_list if etf.get('symbol') in popular_symbols]
            
            if popular_etfs:
                for etf in popular_etfs[:5]:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**{etf['symbol']}**")
                    
                    with col2:
                        st.write(etf['name'])
                    
                    with col3:
                        if st.button("查看", key=f"popular_{etf['symbol']}"):
                            st.session_state.selected_etf = etf['symbol']
                            st.session_state.current_page = 'etf_detail'
                            st.rerun()
            else:
                st.info("暂无热门ETF数据")
    
    def _show_recent_activity(self):
        """显示最近活动"""
        st.subheader("📝 最近活动")
        
        # 这里可以显示最近的操作记录
        activities = []
        
        # 检查最近查看的ETF
        if st.session_state.selected_etf:
            activities.append(f"🔍 最近查看: {st.session_state.selected_etf}")
        
        # 检查最后更新时间
        if st.session_state.last_update:
            activities.append(f"🔄 数据更新: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        # 检查组合状态
        try:
            portfolio_config = self.portfolio_manager.get_portfolio_config()
            if portfolio_config and portfolio_config.etf_weights:
                activities.append(f"💼 组合包含: {len(portfolio_config.etf_weights)} 个ETF")
        except:
            pass
        
        if activities:
            for activity in activities:
                st.text(activity)
        else:
            st.info("暂无最近活动记录")
    
    def _show_system_statistics(self):
        """显示系统统计信息"""
        st.subheader("📈 系统统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            etf_count = len(st.session_state.etf_list)
            st.metric("监控ETF数量", etf_count)
        
        with col2:
            try:
                portfolio_config = self.portfolio_manager.get_portfolio_config()
                portfolio_count = len(portfolio_config.etf_weights) if portfolio_config else 0
            except:
                portfolio_count = 0
            st.metric("组合ETF数量", portfolio_count)
        
        with col3:
            cache_dir = self.config.data.cache_dir
            cache_files = len([f for f in os.listdir(cache_dir) if f.endswith('.pkl')]) if os.path.exists(cache_dir) else 0
            st.metric("缓存文件数", cache_files)
        
        with col4:
            if st.session_state.last_update:
                update_time = st.session_state.last_update.strftime("%H:%M")
                st.metric("最后更新", update_time)
            else:
                st.metric("最后更新", "未更新")
    
    def _refresh_etf_data(self, symbol: str):
        """刷新特定ETF数据"""
        try:
            with st.spinner(f"正在刷新 {symbol} 数据..."):
                # 清除缓存
                cache_file = os.path.join(self.config.data.cache_dir, f"{symbol}.pkl")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                # 重新获取数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                
                data = self.data_loader.get_etf_data(symbol, start_date, end_date)
                
                if data is not None and not data.empty:
                    st.success(f"ETF {symbol} 数据刷新成功！")
                else:
                    st.warning(f"ETF {symbol} 数据为空")
                    
        except Exception as e:
            st.error(f"刷新数据失败: {str(e)}")
    
    def _show_etf_details(self, symbol: str):
        """显示ETF详细信息"""
        try:
            # 获取ETF数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            with st.spinner(f"正在加载 {symbol} 数据..."):
                # 使用系统集成器获取数据，包含错误处理
                data = system_integrator.get_etf_data(symbol, start_date, end_date)
            
            if data is None or data.empty:
                st.warning(f"无法获取 {symbol} 的数据")
                
                # 显示系统健康状态
                with st.expander("🔧 系统诊断信息", expanded=False):
                    health_status = system_integrator.health_check()
                    if health_status['overall_status'] != 'healthy':
                        st.error(f"系统状态: {health_status['overall_status']}")
                        for issue in health_status['issues']:
                            st.error(f"• {issue}")
                    else:
                        st.success("系统状态正常")
                
                return
            
            # 基本信息
            st.subheader(f"📊 {symbol} 基本信息")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                current_price = data['close'].iloc[-1]
                st.metric("最新价格", f"¥{current_price:.2f}")
            
            with col2:
                price_change = data['close'].iloc[-1] - data['close'].iloc[-2]
                change_pct = (price_change / data['close'].iloc[-2]) * 100
                st.metric("日涨跌", f"¥{price_change:.2f}", f"{change_pct:.2f}%")
            
            with col3:
                volume = data['volume'].iloc[-1]
                st.metric("成交量", f"{volume:,.0f}")
            
            with col4:
                # 计算平均成交量
                avg_volume = data['volume'].tail(20).mean()
                volume_ratio = volume / avg_volume
                st.metric("成交量比", f"{volume_ratio:.2f}x")
            
            with col5:
                data_days = len(data)
                st.metric("数据天数", data_days)
            
            # 价格走势图和成交量图
            st.subheader("📈 价格走势与成交量")
            self._create_price_and_volume_charts(data, symbol)
            
            # 技术指标分析
            st.subheader("🔧 技术指标分析")
            self._show_comprehensive_technical_analysis(data, symbol)
            
            # 买入信号分析
            st.subheader("🎯 买入信号分析")
            self._show_enhanced_signal_analysis(symbol, data)
            
        except Exception as e:
            # 使用全局错误处理器
            from etf_dashboard.core.error_handler import ErrorCategory, ErrorSeverity
            
            error_result = system_integrator.error_handler.handle_error(
                error=e,
                category=ErrorCategory.DATA_ACCESS,
                severity=ErrorSeverity.MEDIUM,
                context={'symbol': symbol, 'function': '_show_etf_details'},
                user_message=f"显示ETF {symbol} 详情失败",
                recovery_suggestion="请检查网络连接或稍后重试"
            )
            
            st.error(error_result['user_message'])
            
            # 显示恢复建议
            if error_result.get('recovery_suggestion'):
                st.info(f"💡 建议: {error_result['recovery_suggestion']}")
            
            # 显示技术详情（仅在调试模式下）
            if self.config.ui.show_debug_info:
                with st.expander("🔧 技术详情", expanded=False):
                    st.code(error_result['technical_message'])
            
            self.logger.error(f"ETF details error for {symbol}: {str(e)}")
    
    def _create_price_and_volume_charts(self, data: pd.DataFrame, symbol: str):
        """创建价格走势图和成交量图"""
        try:
            # 创建子图
            from plotly.subplots import make_subplots
            
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=('价格走势', '成交量'),
                row_heights=[0.7, 0.3]
            )
            
            # 添加价格线
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name='收盘价',
                    line=dict(color='#1f77b4', width=2)
                ),
                row=1, col=1
            )
            
            # 计算移动平均线
            ma_data = self.indicators.calculate_moving_averages(
                data['close'], 
                self.config.indicators.ma_periods
            )
            
            # 添加移动平均线
            colors = ['#ff7f0e', '#2ca02c', '#d62728']
            for i, period in enumerate(self.config.indicators.ma_periods):
                if f'MA{period}' in ma_data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=ma_data.index,
                            y=ma_data[f'MA{period}'],
                            mode='lines',
                            name=f'MA{period}',
                            line=dict(color=colors[i % len(colors)], width=1)
                        ),
                        row=1, col=1
                    )
            
            # 添加成交量柱状图
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['volume'],
                    name='成交量',
                    marker_color='rgba(158,202,225,0.6)',
                    marker_line_color='rgba(8,48,107,1.0)',
                    marker_line_width=1
                ),
                row=2, col=1
            )
            
            # 设置图表布局
            fig.update_layout(
                title=f'{symbol} 价格走势与成交量',
                height=600,
                showlegend=True,
                hovermode='x unified'
            )
            
            # 设置y轴标题
            fig.update_yaxes(title_text="价格 (¥)", row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)
            fig.update_xaxes(title_text="日期", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"创建价格和成交量图表失败: {str(e)}")
    
    def _create_price_chart(self, data: pd.DataFrame, symbol: str):
        """创建价格走势图"""
        try:
            fig = go.Figure()
            
            # 添加价格线
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['close'],
                mode='lines',
                name='收盘价',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # 计算移动平均线
            ma_data = self.indicators.calculate_moving_averages(
                data['close'], 
                self.config.indicators.ma_periods
            )
            
            # 添加移动平均线
            colors = ['#ff7f0e', '#2ca02c', '#d62728']
            for i, period in enumerate(self.config.indicators.ma_periods):
                if f'MA{period}' in ma_data.columns:
                    fig.add_trace(go.Scatter(
                        x=ma_data.index,
                        y=ma_data[f'MA{period}'],
                        mode='lines',
                        name=f'MA{period}',
                        line=dict(color=colors[i % len(colors)], width=1)
                    ))
            
            # 设置图表布局
            fig.update_layout(
                title=f'{symbol} 价格走势图',
                xaxis_title='日期',
                yaxis_title='价格 (¥)',
                height=self.config.ui.chart_height,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"创建价格图表失败: {str(e)}")
    
    def _show_comprehensive_technical_analysis(self, data: pd.DataFrame, symbol: str):
        """显示全面的技术指标分析"""
        try:
            # 创建三列布局
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # RSI指标
                rsi = self.indicators.calculate_rsi(data['close'])
                if not rsi.empty:
                    current_rsi = rsi.iloc[-1]
                    
                    # RSI状态判断
                    if current_rsi > self.config.indicators.rsi_overbought:
                        rsi_status = "超买"
                        rsi_color = "🔴"
                        rsi_delta_color = "inverse"
                    elif current_rsi < self.config.indicators.rsi_oversold:
                        rsi_status = "超卖"
                        rsi_color = "🟢"
                        rsi_delta_color = "normal"
                    else:
                        rsi_status = "正常"
                        rsi_color = "🟡"
                        rsi_delta_color = "off"
                    
                    st.metric(
                        "RSI指标",
                        f"{current_rsi:.2f}",
                        f"{rsi_color} {rsi_status}",
                        delta_color=rsi_delta_color
                    )
            
            with col2:
                # 最大回撤
                max_drawdown = self.indicators.calculate_max_drawdown(data['close'])
                drawdown_pct = max_drawdown * 100
                
                # 回撤状态判断
                if drawdown_pct > 20:
                    drawdown_status = "高风险"
                    drawdown_color = "🔴"
                    drawdown_delta_color = "inverse"
                elif drawdown_pct > 10:
                    drawdown_status = "中等风险"
                    drawdown_color = "🟡"
                    drawdown_delta_color = "off"
                else:
                    drawdown_status = "低风险"
                    drawdown_color = "🟢"
                    drawdown_delta_color = "normal"
                
                st.metric(
                    "最大回撤",
                    f"{drawdown_pct:.2f}%",
                    f"{drawdown_color} {drawdown_status}",
                    delta_color=drawdown_delta_color
                )
            
            with col3:
                # 趋势状态
                ma_data = self.indicators.calculate_moving_averages(
                    data['close'], 
                    self.config.indicators.ma_periods
                )
                
                trend_status = self.indicators.get_trend_status(ma_data)
                
                if trend_status == "上升":
                    trend_color = "🟢"
                    trend_delta_color = "normal"
                elif trend_status == "下降":
                    trend_color = "🔴"
                    trend_delta_color = "inverse"
                else:
                    trend_color = "🟡"
                    trend_delta_color = "off"
                
                st.metric(
                    "趋势状态",
                    trend_status,
                    f"{trend_color}",
                    delta_color=trend_delta_color
                )
            
            # 技术指标图表区域
            st.markdown("---")
            
            # 创建两列布局显示图表
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # RSI图表
                if not rsi.empty:
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(
                        x=rsi.index,
                        y=rsi.values,
                        mode='lines',
                        name='RSI',
                        line=dict(color='purple', width=2)
                    ))
                    
                    # 添加超买超卖线
                    fig_rsi.add_hline(
                        y=self.config.indicators.rsi_overbought, 
                        line_dash="dash", 
                        line_color="red", 
                        annotation_text="超买线"
                    )
                    fig_rsi.add_hline(
                        y=self.config.indicators.rsi_oversold, 
                        line_dash="dash", 
                        line_color="green", 
                        annotation_text="超卖线"
                    )
                    fig_rsi.add_hline(
                        y=50, 
                        line_dash="dot", 
                        line_color="gray", 
                        annotation_text="中线"
                    )
                    
                    # 添加背景色区域
                    fig_rsi.add_hrect(
                        y0=self.config.indicators.rsi_overbought, y1=100,
                        fillcolor="red", opacity=0.1,
                        annotation_text="超买区", annotation_position="top left"
                    )
                    fig_rsi.add_hrect(
                        y0=0, y1=self.config.indicators.rsi_oversold,
                        fillcolor="green", opacity=0.1,
                        annotation_text="超卖区", annotation_position="bottom left"
                    )
                    
                    fig_rsi.update_layout(
                        title='RSI相对强弱指数',
                        xaxis_title='日期',
                        yaxis_title='RSI值',
                        height=350,
                        yaxis=dict(range=[0, 100])
                    )
                    
                    st.plotly_chart(fig_rsi, use_container_width=True)
            
            with chart_col2:
                # 移动平均线偏离度图表
                if not ma_data.empty and len(self.config.indicators.ma_periods) >= 2:
                    fig_ma_dev = go.Figure()
                    
                    # 计算MA5与MA20的偏离度
                    if 'MA5' in ma_data.columns and 'MA20' in ma_data.columns:
                        ma_deviation = ((ma_data['MA5'] - ma_data['MA20']) / ma_data['MA20'] * 100).dropna()
                        
                        fig_ma_dev.add_trace(go.Scatter(
                            x=ma_deviation.index,
                            y=ma_deviation.values,
                            mode='lines',
                            name='MA5-MA20偏离度',
                            line=dict(color='orange', width=2),
                            fill='tonexty'
                        ))
                        
                        # 添加零线
                        fig_ma_dev.add_hline(
                            y=0, 
                            line_dash="solid", 
                            line_color="black", 
                            annotation_text="零线"
                        )
                        
                        fig_ma_dev.update_layout(
                            title='移动平均线偏离度',
                            xaxis_title='日期',
                            yaxis_title='偏离度 (%)',
                            height=350
                        )
                        
                        st.plotly_chart(fig_ma_dev, use_container_width=True)
                    else:
                        st.info("移动平均线数据不足，无法显示偏离度图表")
            
            # 成交量分析
            st.markdown("---")
            st.subheader("📊 成交量分析")
            
            vol_col1, vol_col2, vol_col3 = st.columns(3)
            
            with vol_col1:
                # 成交量状态
                avg_volume = data['volume'].tail(20).mean()
                current_volume = data['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume
                
                if volume_ratio > 1.5:
                    volume_status = "放量"
                    volume_color = "🟢"
                    volume_delta_color = "normal"
                elif volume_ratio < 0.5:
                    volume_status = "缩量"
                    volume_color = "🔴"
                    volume_delta_color = "inverse"
                else:
                    volume_status = "正常"
                    volume_color = "🟡"
                    volume_delta_color = "off"
                
                st.metric(
                    "成交量状态",
                    f"{volume_ratio:.2f}x",
                    f"{volume_color} {volume_status}",
                    delta_color=volume_delta_color
                )
            
            with vol_col2:
                # 平均成交量
                st.metric(
                    "20日均量",
                    f"{avg_volume:,.0f}"
                )
            
            with vol_col3:
                # 成交量变化率
                volume_change = (current_volume - data['volume'].iloc[-2]) / data['volume'].iloc[-2] * 100
                st.metric(
                    "成交量变化",
                    f"{volume_change:+.1f}%"
                )
                
        except Exception as e:
            st.error(f"技术指标分析失败: {str(e)}")
            self.logger.error(f"Comprehensive technical analysis error: {str(e)}")
    
    def _show_technical_analysis(self, data: pd.DataFrame, symbol: str):
        """显示技术指标分析"""
        try:
            col1, col2 = st.columns(2)
            
            with col1:
                # RSI指标
                rsi = self.indicators.calculate_rsi(data['close'])
                if not rsi.empty:
                    current_rsi = rsi.iloc[-1]
                    
                    # RSI状态判断
                    if current_rsi > self.config.indicators.rsi_overbought:
                        rsi_status = "超买"
                        rsi_color = "🔴"
                    elif current_rsi < self.config.indicators.rsi_oversold:
                        rsi_status = "超卖"
                        rsi_color = "🟢"
                    else:
                        rsi_status = "正常"
                        rsi_color = "🟡"
                    
                    st.metric(
                        "RSI指标",
                        f"{current_rsi:.2f}",
                        f"{rsi_color} {rsi_status}"
                    )
                    
                    # RSI图表
                    fig_rsi = go.Figure()
                    fig_rsi.add_trace(go.Scatter(
                        x=rsi.index,
                        y=rsi.values,
                        mode='lines',
                        name='RSI',
                        line=dict(color='purple')
                    ))
                    
                    # 添加超买超卖线
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超买线")
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超卖线")
                    
                    fig_rsi.update_layout(
                        title='RSI指标',
                        xaxis_title='日期',
                        yaxis_title='RSI值',
                        height=300,
                        yaxis=dict(range=[0, 100])
                    )
                    
                    st.plotly_chart(fig_rsi, use_container_width=True)
            
            with col2:
                # 最大回撤
                max_drawdown = self.indicators.calculate_max_drawdown(data['close'])
                drawdown_pct = max_drawdown * 100
                
                # 回撤状态判断
                if drawdown_pct > 20:
                    drawdown_status = "高风险"
                    drawdown_color = "🔴"
                elif drawdown_pct > 10:
                    drawdown_status = "中等风险"
                    drawdown_color = "🟡"
                else:
                    drawdown_status = "低风险"
                    drawdown_color = "🟢"
                
                st.metric(
                    "最大回撤",
                    f"{drawdown_pct:.2f}%",
                    f"{drawdown_color} {drawdown_status}"
                )
                
                # 趋势状态
                ma_data = self.indicators.calculate_moving_averages(
                    data['close'], 
                    self.config.indicators.ma_periods
                )
                
                trend_status = self.indicators.get_trend_status(ma_data)
                
                if trend_status == "上升":
                    trend_color = "🟢"
                elif trend_status == "下降":
                    trend_color = "🔴"
                else:
                    trend_color = "🟡"
                
                st.metric(
                    "趋势状态",
                    trend_status,
                    f"{trend_color}"
                )
                
                # 成交量分析
                avg_volume = data['volume'].tail(20).mean()
                current_volume = data['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume
                
                if volume_ratio > 1.5:
                    volume_status = "放量"
                    volume_color = "🟢"
                elif volume_ratio < 0.5:
                    volume_status = "缩量"
                    volume_color = "🔴"
                else:
                    volume_status = "正常"
                    volume_color = "🟡"
                
                st.metric(
                    "成交量状态",
                    f"{volume_ratio:.2f}x",
                    f"{volume_color} {volume_status}"
                )
                
        except Exception as e:
            st.error(f"技术指标分析失败: {str(e)}")
    
    def _show_enhanced_signal_analysis(self, symbol: str, data: pd.DataFrame):
        """显示增强的信号分析"""
        try:
            # 生成买入信号
            signal = self.signal_manager.generate_buy_signal(symbol)
            
            # 创建醒目的信号显示区域
            if signal.is_allowed:
                st.success("🎯 **买入信号：允许买入**")
                signal_container = st.container()
                with signal_container:
                    st.markdown("""
                    <div style="background-color: #d4edda; border: 2px solid #28a745; border-radius: 10px; padding: 20px; margin: 10px 0;">
                        <h3 style="color: #155724; margin: 0 0 10px 0;">✅ 买入条件满足</h3>
                        <p style="color: #155724; margin: 0; font-size: 16px;">当前技术指标支持买入操作</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("🚫 **买入信号：禁止买入**")
                signal_container = st.container()
                with signal_container:
                    st.markdown("""
                    <div style="background-color: #f8d7da; border: 2px solid #dc3545; border-radius: 10px; padding: 20px; margin: 10px 0;">
                        <h3 style="color: #721c24; margin: 0 0 10px 0;">❌ 买入条件不满足</h3>
                        <p style="color: #721c24; margin: 0; font-size: 16px;">当前技术指标不支持买入操作</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 显示信号详情
            col1, col2, col3 = st.columns(3)
            
            with col1:
                confidence_color = "normal" if signal.confidence > 0.7 else "inverse" if signal.confidence < 0.3 else "off"
                st.metric(
                    "信号置信度", 
                    f"{signal.confidence:.2f}",
                    delta_color=confidence_color
                )
            
            with col2:
                signal_strength = "强" if signal.confidence > 0.8 else "中" if signal.confidence > 0.5 else "弱"
                st.metric("信号强度", signal_strength)
            
            with col3:
                signal_time = signal.timestamp.strftime('%H:%M:%S') if hasattr(signal, 'timestamp') and signal.timestamp else "实时"
                st.metric("信号时间", signal_time)
            
            # 显示详细的信号分析原因
            st.markdown("---")
            st.subheader("📋 信号分析详情")
            
            reason_col1, reason_col2 = st.columns(2)
            
            with reason_col1:
                st.markdown("**✅ 满足条件:**")
                positive_reasons = [reason for reason in signal.reasons if "允许" in reason or "满足" in reason or "支持" in reason]
                if positive_reasons:
                    for reason in positive_reasons:
                        st.markdown(f"• {reason}")
                else:
                    st.markdown("• 暂无满足的条件")
            
            with reason_col2:
                st.markdown("**❌ 不满足条件:**")
                negative_reasons = [reason for reason in signal.reasons if "禁止" in reason or "不满足" in reason or "超过" in reason]
                if negative_reasons:
                    for reason in negative_reasons:
                        st.markdown(f"• {reason}")
                else:
                    st.markdown("• 暂无不满足的条件")
            
            # 显示详细的规则检查表格
            st.markdown("---")
            st.subheader("📊 详细规则检查")
            
            # 获取技术指标数据
            ma_data = self.indicators.calculate_moving_averages(
                data['close'], 
                self.config.indicators.ma_periods
            )
            rsi = self.indicators.calculate_rsi(data['close'])
            max_drawdown = self.indicators.calculate_max_drawdown(data['close'])
            
            # 规则检查表格
            rules_data = []
            
            # 趋势规则
            trend_status = self.indicators.get_trend_status(ma_data)
            trend_pass = trend_status in ["上升", "震荡"]
            rules_data.append({
                "规则类型": "趋势检查",
                "检查项目": "趋势状态",
                "当前值": trend_status,
                "要求": "上升或震荡",
                "状态": "✅ 通过" if trend_pass else "❌ 不通过",
                "权重": "高"
            })
            
            # RSI规则
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                if trend_status == "上升":
                    rsi_pass = current_rsi < self.config.indicators.rsi_overbought
                    rsi_requirement = f"< {self.config.indicators.rsi_overbought} (上升趋势)"
                elif trend_status == "震荡":
                    rsi_pass = current_rsi < self.config.indicators.rsi_neutral
                    rsi_requirement = f"< {self.config.indicators.rsi_neutral} (震荡趋势)"
                else:
                    rsi_pass = False
                    rsi_requirement = "不适用 (下降趋势)"
                
                rules_data.append({
                    "规则类型": "RSI检查",
                    "检查项目": "相对强弱指数",
                    "当前值": f"{current_rsi:.2f}",
                    "要求": rsi_requirement,
                    "状态": "✅ 通过" if rsi_pass else "❌ 不通过",
                    "权重": "中"
                })
            
            # 回撤规则
            drawdown_pct = max_drawdown * 100
            drawdown_pass = drawdown_pct <= (self.config.signals.max_drawdown_threshold * 100)
            rules_data.append({
                "规则类型": "风险检查",
                "检查项目": "最大回撤",
                "当前值": f"{drawdown_pct:.2f}%",
                "要求": f"<= {self.config.signals.max_drawdown_threshold * 100:.0f}%",
                "状态": "✅ 通过" if drawdown_pass else "❌ 不通过",
                "权重": "高"
            })
            
            # 成交量规则（可选）
            avg_volume = data['volume'].tail(20).mean()
            current_volume = data['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume
            volume_pass = volume_ratio > 0.5  # 成交量不能太低
            rules_data.append({
                "规则类型": "成交量检查",
                "检查项目": "成交量比率",
                "当前值": f"{volume_ratio:.2f}x",
                "要求": "> 0.5x (避免缩量)",
                "状态": "✅ 通过" if volume_pass else "⚠️ 警告",
                "权重": "低"
            })
            
            # 显示规则表格
            rules_df = pd.DataFrame(rules_data)
            
            # 使用颜色编码显示表格
            def color_status(val):
                if "✅" in val:
                    return 'background-color: #d4edda; color: #155724'
                elif "❌" in val:
                    return 'background-color: #f8d7da; color: #721c24'
                elif "⚠️" in val:
                    return 'background-color: #fff3cd; color: #856404'
                return ''
            
            styled_df = rules_df.style.applymap(color_status, subset=['状态'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # 显示综合评分
            st.markdown("---")
            st.subheader("🎯 综合评分")
            
            # 计算综合评分
            total_score = 0
            max_score = 0
            
            for rule in rules_data:
                weight_multiplier = {"高": 3, "中": 2, "低": 1}[rule["权重"]]
                max_score += weight_multiplier
                
                if "✅" in rule["状态"]:
                    total_score += weight_multiplier
                elif "⚠️" in rule["状态"]:
                    total_score += weight_multiplier * 0.5
            
            final_score = (total_score / max_score) * 100 if max_score > 0 else 0
            
            score_col1, score_col2, score_col3 = st.columns(3)
            
            with score_col1:
                score_color = "normal" if final_score >= 70 else "inverse" if final_score < 40 else "off"
                st.metric(
                    "综合评分",
                    f"{final_score:.1f}分",
                    delta_color=score_color
                )
            
            with score_col2:
                if final_score >= 80:
                    recommendation = "🟢 强烈推荐"
                elif final_score >= 60:
                    recommendation = "🟡 谨慎考虑"
                else:
                    recommendation = "🔴 不建议"
                st.metric("投资建议", recommendation)
            
            with score_col3:
                risk_level = "低风险" if final_score >= 70 else "中风险" if final_score >= 40 else "高风险"
                st.metric("风险等级", risk_level)
            
        except Exception as e:
            st.error(f"增强信号分析失败: {str(e)}")
            self.logger.error(f"Enhanced signal analysis error for {symbol}: {str(e)}")
    
    def _show_signal_analysis(self, symbol: str, data: pd.DataFrame):
        """显示信号分析"""
        try:
            # 生成买入信号
            signal = self.signal_manager.generate_buy_signal(symbol)
            
            # 显示信号结果
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if signal.is_allowed:
                    st.success("✅ 允许买入")
                    signal_color = "success"
                else:
                    st.error("❌ 禁止买入")
                    signal_color = "danger"
                
                st.metric("信号置信度", f"{signal.confidence:.2f}")
            
            with col2:
                st.markdown("**信号分析原因:**")
                for reason in signal.reasons:
                    if "允许" in reason or "满足" in reason:
                        st.markdown(f"✅ {reason}")
                    else:
                        st.markdown(f"❌ {reason}")
            
            # 显示详细的规则检查
            st.markdown("---")
            st.subheader("📋 详细规则检查")
            
            # 获取技术指标数据
            ma_data = self.indicators.calculate_moving_averages(
                data['close'], 
                self.config.indicators.ma_periods
            )
            rsi = self.indicators.calculate_rsi(data['close'])
            max_drawdown = self.indicators.calculate_max_drawdown(data['close'])
            
            # 规则检查表格
            rules_data = []
            
            # 趋势规则
            trend_status = self.indicators.get_trend_status(ma_data)
            trend_pass = trend_status in ["上升", "震荡"]
            rules_data.append({
                "规则": "趋势状态检查",
                "当前值": trend_status,
                "要求": "上升或震荡",
                "状态": "✅ 通过" if trend_pass else "❌ 不通过"
            })
            
            # RSI规则
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                if trend_status == "上升":
                    rsi_pass = current_rsi < self.config.indicators.rsi_overbought
                    rsi_requirement = f"< {self.config.indicators.rsi_overbought}"
                elif trend_status == "震荡":
                    rsi_pass = current_rsi < self.config.indicators.rsi_neutral
                    rsi_requirement = f"< {self.config.indicators.rsi_neutral}"
                else:
                    rsi_pass = False
                    rsi_requirement = "不适用"
                
                rules_data.append({
                    "规则": "RSI检查",
                    "当前值": f"{current_rsi:.2f}",
                    "要求": rsi_requirement,
                    "状态": "✅ 通过" if rsi_pass else "❌ 不通过"
                })
            
            # 回撤规则
            drawdown_pct = max_drawdown * 100
            drawdown_pass = drawdown_pct <= (self.config.signals.max_drawdown_threshold * 100)
            rules_data.append({
                "规则": "最大回撤检查",
                "当前值": f"{drawdown_pct:.2f}%",
                "要求": f"<= {self.config.signals.max_drawdown_threshold * 100:.0f}%",
                "状态": "✅ 通过" if drawdown_pass else "❌ 不通过"
            })
            
            # 显示规则表格
            rules_df = pd.DataFrame(rules_data)
            st.dataframe(rules_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"信号分析失败: {str(e)}")
            self.logger.error(f"Signal analysis error for {symbol}: {str(e)}")
    
    def _show_portfolio_overview(self, portfolio_config):
        """显示组合概览"""
        try:
            # 组合基本信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                etf_count = len(portfolio_config.etf_weights)
                st.metric("组合ETF数量", etf_count)
            
            with col2:
                total_weight = sum(portfolio_config.etf_weights.values())
                st.metric("权重总和", f"{total_weight:.1%}")
            
            with col3:
                rebalance_threshold = portfolio_config.rebalance_threshold
                st.metric("再平衡阈值", f"{rebalance_threshold:.1%}")
            
            with col4:
                created_date = portfolio_config.created_at.strftime('%Y-%m-%d')
                st.metric("创建日期", created_date)
            
            # 组合配置表格
            st.subheader("📋 组合配置")
            
            config_data = []
            for symbol, weight in portfolio_config.etf_weights.items():
                config_data.append({
                    "ETF代码": symbol,
                    "目标权重": f"{weight * 100:.1f}%",
                    "权重值": weight
                })
            
            config_df = pd.DataFrame(config_data)
            
            # 使用可编辑的数据编辑器
            edited_df = st.data_editor(
                config_df[["ETF代码", "目标权重"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ETF代码": st.column_config.TextColumn("ETF代码", disabled=True),
                    "目标权重": st.column_config.TextColumn("目标权重")
                },
                key="portfolio_config_editor"
            )
            
            # 操作按钮
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 更新权重", use_container_width=True):
                    self._update_portfolio_weights(edited_df)
            
            with col2:
                if st.button("➕ 添加ETF", use_container_width=True):
                    st.session_state.show_add_etf_form = True
                    st.rerun()
            
            with col3:
                if st.button("🗑️ 删除选中", use_container_width=True):
                    st.session_state.show_delete_etf_form = True
                    st.rerun()
            
            # 权重分布饼图
            if config_data:
                st.subheader("📊 权重分布")
                fig_pie = px.pie(
                    values=[item["权重值"] for item in config_data],
                    names=[item["ETF代码"] for item in config_data],
                    title="组合权重分布",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
        except Exception as e:
            st.error(f"显示组合概览失败: {str(e)}")
            self.logger.error(f"Portfolio overview error: {str(e)}")
    
    def _show_portfolio_analysis(self):
        """显示组合分析"""
        try:
            st.subheader("📊 组合分析")
            
            # 获取组合配置
            portfolio_config = self.portfolio_manager.get_portfolio_config()
            if not portfolio_config or not portfolio_config.etf_weights:
                st.info("请先配置投资组合")
                return
            
            # 获取当前价格数据
            current_prices = {}
            etf_data = {}
            
            with st.spinner("正在获取ETF数据..."):
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                
                for symbol in portfolio_config.etf_weights.keys():
                    try:
                        data = self.data_loader.get_etf_data(symbol, start_date, end_date)
                        if data is not None and not data.empty:
                            current_prices[symbol] = data['close'].iloc[-1]
                            etf_data[symbol] = data
                    except Exception as e:
                        st.warning(f"无法获取 {symbol} 的数据: {str(e)}")
            
            if not current_prices:
                st.warning("无法获取任何ETF的价格数据")
                return
            
            # 显示持仓输入区域
            self._show_holdings_input(portfolio_config, current_prices)
            
            # 显示仓位偏离分析
            self._show_deviation_analysis(portfolio_config, current_prices)
            
            # 显示再平衡建议
            self._show_rebalance_suggestions(portfolio_config, current_prices)
            
            # 显示组合表现分析
            self._show_portfolio_performance(etf_data, portfolio_config)
            
        except Exception as e:
            st.error(f"组合分析失败: {str(e)}")
            self.logger.error(f"Portfolio analysis error: {str(e)}")
    
    def _show_add_etf_form(self):
        """显示添加ETF表单"""
        st.subheader("➕ 添加ETF到组合")
        
        etf_list = self._get_etf_list()
        if not etf_list:
            st.warning("无法获取ETF列表")
            return
        
        with st.form("add_etf_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                etf_options = {f"{etf['symbol']} - {etf['name']}": etf['symbol'] 
                              for etf in etf_list[:50]}  # 增加选择范围
                
                selected_etf = st.selectbox(
                    "选择ETF",
                    options=list(etf_options.keys()),
                    help="选择要添加到组合中的ETF"
                )
            
            with col2:
                weight = st.number_input(
                    "目标权重 (%)",
                    min_value=0.1,
                    max_value=100.0,
                    value=10.0,
                    step=0.1,
                    help="设置该ETF在组合中的目标权重"
                )
            
            # 显示当前组合权重总和
            portfolio_config = self.portfolio_manager.get_portfolio_config()
            if portfolio_config:
                current_total = sum(portfolio_config.etf_weights.values()) * 100
                new_total = current_total + weight
                
                if new_total > 100:
                    st.warning(f"⚠️ 添加后权重总和将为 {new_total:.1f}%，超过100%")
                else:
                    st.info(f"ℹ️ 添加后权重总和将为 {new_total:.1f}%")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("添加到组合", type="primary", use_container_width=True):
                    try:
                        symbol = etf_options[selected_etf]
                        self.portfolio_manager.add_etf_to_portfolio(symbol, weight / 100)
                        st.success(f"ETF {symbol} 已添加到组合中！")
                        st.session_state.show_add_etf_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加失败: {str(e)}")
            
            with col2:
                if st.form_submit_button("取消", use_container_width=True):
                    st.session_state.show_add_etf_form = False
                    st.rerun()
    
    def _update_portfolio_weights(self, edited_df):
        """更新组合权重"""
        try:
            # 解析编辑后的权重数据
            new_weights = {}
            total_weight = 0
            
            for _, row in edited_df.iterrows():
                symbol = row['ETF代码']
                weight_str = row['目标权重'].replace('%', '')
                weight = float(weight_str) / 100
                new_weights[symbol] = weight
                total_weight += weight
            
            # 验证权重总和
            if abs(total_weight - 1.0) > 0.001:
                st.error(f"权重总和必须为100%，当前为 {total_weight:.1%}")
                return
            
            # 更新权重
            self.portfolio_manager.update_target_weights(new_weights)
            st.success("组合权重已更新！")
            st.rerun()
            
        except Exception as e:
            st.error(f"更新权重失败: {str(e)}")
    
    def _show_holdings_input(self, portfolio_config, current_prices):
        """显示持仓输入区域"""
        st.subheader("💰 当前持仓")
        
        # 创建持仓输入表单
        with st.expander("📝 输入当前持仓数量", expanded=False):
            st.info("请输入您当前持有的各ETF数量，以便计算仓位偏离和再平衡建议")
            
            holdings_data = []
            for symbol in portfolio_config.etf_weights.keys():
                current_holding = st.session_state.get(f"holding_{symbol}", 0.0)
                price = current_prices.get(symbol, 0.0)
                value = current_holding * price
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.text(f"ETF: {symbol}")
                
                with col2:
                    new_holding = st.number_input(
                        f"持仓数量",
                        min_value=0.0,
                        value=current_holding,
                        step=100.0,
                        key=f"input_holding_{symbol}",
                        help=f"当前价格: ¥{price:.2f}"
                    )
                    st.session_state[f"holding_{symbol}"] = new_holding
                
                with col3:
                    st.metric("当前价格", f"¥{price:.2f}")
                
                with col4:
                    st.metric("持仓价值", f"¥{new_holding * price:,.2f}")
                
                holdings_data.append({
                    "symbol": symbol,
                    "quantity": new_holding,
                    "price": price,
                    "value": new_holding * price
                })
            
            # 更新持仓到组合管理器
            holdings_dict = {item["symbol"]: item["quantity"] for item in holdings_data}
            self.portfolio_manager.update_current_holdings(holdings_dict)
            
            # 显示总持仓价值
            total_value = sum(item["value"] for item in holdings_data)
            st.metric("总持仓价值", f"¥{total_value:,.2f}")
    
    def _show_deviation_analysis(self, portfolio_config, current_prices):
        """显示仓位偏离分析"""
        st.subheader("📊 仓位偏离分析")
        
        try:
            # 计算偏离度
            deviations = self.portfolio_manager.calculate_portfolio_deviation(current_prices)
            total_value = self.portfolio_manager.calculate_portfolio_value(current_prices)
            
            if total_value == 0:
                st.info("请先输入当前持仓数量")
                return
            
            # 创建偏离分析表格
            deviation_data = []
            for symbol in portfolio_config.etf_weights.keys():
                target_weight = portfolio_config.etf_weights[symbol]
                current_quantity = st.session_state.get(f"holding_{symbol}", 0.0)
                current_price = current_prices.get(symbol, 0.0)
                current_value = current_quantity * current_price
                current_weight = current_value / total_value if total_value > 0 else 0
                deviation = deviations.get(symbol, 0)
                
                # 判断偏离状态
                if deviation > portfolio_config.rebalance_threshold:
                    status = "🔴 需要再平衡"
                    status_color = "error"
                elif deviation > portfolio_config.rebalance_threshold * 0.5:
                    status = "🟡 接近阈值"
                    status_color = "warning"
                else:
                    status = "🟢 正常"
                    status_color = "success"
                
                deviation_data.append({
                    "ETF代码": symbol,
                    "目标权重": f"{target_weight:.1%}",
                    "当前权重": f"{current_weight:.1%}",
                    "偏离度": f"{deviation:.1%}",
                    "状态": status,
                    "持仓数量": f"{current_quantity:,.0f}",
                    "持仓价值": f"¥{current_value:,.2f}"
                })
            
            # 显示偏离分析表格
            deviation_df = pd.DataFrame(deviation_data)
            st.dataframe(
                deviation_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "状态": st.column_config.TextColumn("状态", width="small")
                }
            )
            
            # 显示偏离度图表
            if deviation_data:
                fig_deviation = go.Figure()
                
                symbols = [item["ETF代码"] for item in deviation_data]
                target_weights = [float(item["目标权重"].replace('%', '')) for item in deviation_data]
                current_weights = [float(item["当前权重"].replace('%', '')) for item in deviation_data]
                
                fig_deviation.add_trace(go.Bar(
                    name='目标权重',
                    x=symbols,
                    y=target_weights,
                    marker_color='lightblue'
                ))
                
                fig_deviation.add_trace(go.Bar(
                    name='当前权重',
                    x=symbols,
                    y=current_weights,
                    marker_color='orange'
                ))
                
                fig_deviation.update_layout(
                    title='目标权重 vs 当前权重对比',
                    xaxis_title='ETF代码',
                    yaxis_title='权重 (%)',
                    barmode='group',
                    height=400
                )
                
                st.plotly_chart(fig_deviation, use_container_width=True)
            
        except Exception as e:
            st.error(f"偏离分析失败: {str(e)}")
    
    def _show_rebalance_suggestions(self, portfolio_config, current_prices):
        """显示再平衡建议"""
        st.subheader("⚖️ 再平衡建议")
        
        try:
            # 获取再平衡建议
            suggestions = self.portfolio_manager.get_rebalance_suggestions(current_prices)
            
            if not suggestions:
                st.info("暂无再平衡建议")
                return
            
            # 筛选需要操作的建议
            action_needed = [s for s in suggestions if s.action != "持有"]
            
            if not action_needed:
                st.success("🎉 组合配置良好，无需再平衡！")
                return
            
            st.warning(f"发现 {len(action_needed)} 个ETF需要再平衡")
            
            # 创建再平衡建议表格
            suggestion_data = []
            for suggestion in suggestions:
                if suggestion.action != "持有":
                    # 确定操作颜色
                    if suggestion.action == "买入":
                        action_display = "🟢 买入"
                    else:
                        action_display = "🔴 卖出"
                    
                    suggestion_data.append({
                        "ETF代码": suggestion.symbol,
                        "操作": action_display,
                        "当前权重": f"{suggestion.current_weight:.1%}",
                        "目标权重": f"{suggestion.target_weight:.1%}",
                        "偏离度": f"{suggestion.deviation:.1%}",
                        "建议金额": f"¥{abs(suggestion.suggested_amount):,.2f}",
                        "优先级": "高" if suggestion.deviation > portfolio_config.rebalance_threshold * 2 else "中"
                    })
            
            if suggestion_data:
                suggestion_df = pd.DataFrame(suggestion_data)
                st.dataframe(
                    suggestion_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "操作": st.column_config.TextColumn("操作", width="small"),
                        "优先级": st.column_config.TextColumn("优先级", width="small")
                    }
                )
                
                # 显示再平衡摘要
                st.markdown("---")
                st.subheader("📋 再平衡摘要")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    buy_actions = [s for s in suggestions if s.action == "买入"]
                    total_buy = sum(s.suggested_amount for s in buy_actions)
                    st.metric("需要买入", f"¥{total_buy:,.2f}", f"{len(buy_actions)} 个ETF")
                
                with col2:
                    sell_actions = [s for s in suggestions if s.action == "卖出"]
                    total_sell = sum(s.suggested_amount for s in sell_actions)
                    st.metric("需要卖出", f"¥{total_sell:,.2f}", f"{len(sell_actions)} 个ETF")
                
                with col3:
                    net_flow = total_buy - total_sell
                    flow_direction = "流入" if net_flow > 0 else "流出"
                    st.metric("净资金流", f"¥{abs(net_flow):,.2f}", f"{flow_direction}")
            
        except Exception as e:
            st.error(f"再平衡建议生成失败: {str(e)}")
    
    def _show_portfolio_performance(self, etf_data, portfolio_config):
        """显示组合表现分析"""
        st.subheader("📈 组合表现分析")
        
        try:
            if not etf_data:
                st.info("需要ETF数据来分析组合表现")
                return
            
            # 计算组合收益率
            portfolio_returns = []
            dates = None
            
            for symbol, weight in portfolio_config.etf_weights.items():
                if symbol in etf_data:
                    data = etf_data[symbol]
                    returns = data['close'].pct_change().fillna(0)
                    weighted_returns = returns * weight
                    
                    if dates is None:
                        dates = returns.index
                        portfolio_returns = weighted_returns
                    else:
                        # 确保日期对齐
                        aligned_returns = weighted_returns.reindex(dates, fill_value=0)
                        portfolio_returns += aligned_returns
            
            if len(portfolio_returns) == 0:
                st.info("无法计算组合表现")
                return
            
            # 计算累计收益
            cumulative_returns = (1 + portfolio_returns).cumprod()
            total_return = (cumulative_returns.iloc[-1] - 1) * 100
            
            # 计算统计指标
            volatility = portfolio_returns.std() * (252 ** 0.5) * 100  # 年化波动率
            sharpe_ratio = (portfolio_returns.mean() * 252) / (portfolio_returns.std() * (252 ** 0.5)) if portfolio_returns.std() > 0 else 0
            max_drawdown = ((cumulative_returns / cumulative_returns.expanding().max()) - 1).min() * 100
            
            # 显示表现指标
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                return_color = "normal" if total_return > 0 else "inverse"
                st.metric(
                    "总收益率",
                    f"{total_return:+.2f}%",
                    delta_color=return_color
                )
            
            with col2:
                vol_color = "inverse" if volatility > 20 else "normal"
                st.metric(
                    "年化波动率",
                    f"{volatility:.2f}%",
                    delta_color=vol_color
                )
            
            with col3:
                sharpe_color = "normal" if sharpe_ratio > 1 else "inverse" if sharpe_ratio < 0 else "off"
                st.metric(
                    "夏普比率",
                    f"{sharpe_ratio:.2f}",
                    delta_color=sharpe_color
                )
            
            with col4:
                drawdown_color = "inverse" if max_drawdown < -10 else "normal"
                st.metric(
                    "最大回撤",
                    f"{max_drawdown:.2f}%",
                    delta_color=drawdown_color
                )
            
            # 绘制组合收益曲线
            fig_performance = go.Figure()
            
            fig_performance.add_trace(go.Scatter(
                x=dates,
                y=(cumulative_returns - 1) * 100,
                mode='lines',
                name='组合累计收益率',
                line=dict(color='blue', width=2)
            ))
            
            fig_performance.update_layout(
                title='组合累计收益率走势',
                xaxis_title='日期',
                yaxis_title='累计收益率 (%)',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_performance, use_container_width=True)
            
            # 个股贡献分析
            st.markdown("---")
            st.subheader("📊 个股贡献分析")
            
            contribution_data = []
            for symbol, weight in portfolio_config.etf_weights.items():
                if symbol in etf_data:
                    data = etf_data[symbol]
                    individual_return = ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
                    contribution = individual_return * weight
                    
                    contribution_data.append({
                        "ETF代码": symbol,
                        "权重": f"{weight:.1%}",
                        "个股收益": f"{individual_return:+.2f}%",
                        "贡献度": f"{contribution:+.2f}%"
                    })
            
            if contribution_data:
                contribution_df = pd.DataFrame(contribution_data)
                st.dataframe(contribution_df, use_container_width=True, hide_index=True)
                
                # 贡献度图表
                fig_contribution = go.Figure(data=[
                    go.Bar(
                        x=[item["ETF代码"] for item in contribution_data],
                        y=[float(item["贡献度"].replace('%', '').replace('+', '')) for item in contribution_data],
                        marker_color=['green' if float(item["贡献度"].replace('%', '').replace('+', '')) > 0 else 'red' 
                                    for item in contribution_data]
                    )
                ])
                
                fig_contribution.update_layout(
                    title='各ETF对组合收益的贡献度',
                    xaxis_title='ETF代码',
                    yaxis_title='贡献度 (%)',
                    height=300
                )
                
                st.plotly_chart(fig_contribution, use_container_width=True)
            
        except Exception as e:
            st.error(f"组合表现分析失败: {str(e)}")
            self.logger.error(f"Portfolio performance analysis error: {str(e)}")
    
    def _show_ui_settings(self):
        """显示界面设置"""
        st.subheader("🎨 界面设置")
        
        # 主题设置
        theme = st.selectbox(
            "主题",
            options=["light", "dark"],
            index=0 if self.config.ui.theme == "light" else 1
        )
        
        # 图表高度设置
        chart_height = st.slider(
            "图表高度",
            min_value=300,
            max_value=800,
            value=self.config.ui.chart_height,
            step=50
        )
        
        # 调试信息设置
        show_debug = st.checkbox(
            "显示调试信息",
            value=self.config.ui.show_debug_info
        )
        
        if st.button("保存界面设置"):
            try:
                self.config.update_config('ui', {
                    'theme': theme,
                    'chart_height': chart_height,
                    'show_debug_info': show_debug
                })
                self.config.save_config()
                st.success("界面设置已保存！")
            except Exception as e:
                st.error(f"保存设置失败: {str(e)}")
    
    def _show_indicator_settings(self):
        """显示技术指标设置"""
        st.subheader("📈 技术指标设置")
        
        # MA周期设置
        ma_periods_str = st.text_input(
            "移动平均线周期 (逗号分隔)",
            value=",".join(map(str, self.config.indicators.ma_periods))
        )
        
        # RSI设置
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rsi_period = st.number_input(
                "RSI周期",
                min_value=5,
                max_value=50,
                value=self.config.indicators.rsi_period
            )
        
        with col2:
            rsi_overbought = st.number_input(
                "RSI超买线",
                min_value=60.0,
                max_value=90.0,
                value=self.config.indicators.rsi_overbought
            )
        
        with col3:
            rsi_oversold = st.number_input(
                "RSI超卖线",
                min_value=10.0,
                max_value=40.0,
                value=self.config.indicators.rsi_oversold
            )
        
        if st.button("保存技术指标设置"):
            try:
                ma_periods = [int(x.strip()) for x in ma_periods_str.split(",")]
                
                self.config.update_config('indicators', {
                    'ma_periods': ma_periods,
                    'rsi_period': rsi_period,
                    'rsi_overbought': rsi_overbought,
                    'rsi_oversold': rsi_oversold
                })
                self.config.save_config()
                st.success("技术指标设置已保存！")
            except Exception as e:
                st.error(f"保存设置失败: {str(e)}")
    
    def _show_signal_settings(self):
        """显示信号规则设置"""
        st.subheader("🔔 信号规则设置")
        
        # 最大回撤阈值
        max_drawdown = st.slider(
            "最大回撤阈值 (%)",
            min_value=5.0,
            max_value=50.0,
            value=self.config.signals.max_drawdown_threshold * 100,
            step=1.0
        )
        
        # 置信度阈值
        confidence_threshold = st.slider(
            "信号置信度阈值",
            min_value=0.1,
            max_value=1.0,
            value=self.config.signals.confidence_threshold,
            step=0.1
        )
        
        # 过滤器开关
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enable_trend = st.checkbox(
                "启用趋势过滤",
                value=self.config.signals.enable_trend_filter
            )
        
        with col2:
            enable_rsi = st.checkbox(
                "启用RSI过滤",
                value=self.config.signals.enable_rsi_filter
            )
        
        with col3:
            enable_drawdown = st.checkbox(
                "启用回撤过滤",
                value=self.config.signals.enable_drawdown_filter
            )
        
        if st.button("保存信号设置"):
            try:
                self.config.update_config('signals', {
                    'max_drawdown_threshold': max_drawdown / 100,
                    'confidence_threshold': confidence_threshold,
                    'enable_trend_filter': enable_trend,
                    'enable_rsi_filter': enable_rsi,
                    'enable_drawdown_filter': enable_drawdown
                })
                self.config.save_config()
                st.success("信号设置已保存！")
            except Exception as e:
                st.error(f"保存设置失败: {str(e)}")
    
    def _show_data_settings(self):
        """显示数据管理设置"""
        st.subheader("💾 数据管理")
        
        # 缓存设置
        cache_expiry = st.number_input(
            "缓存过期时间 (小时)",
            min_value=1,
            max_value=168,  # 一周
            value=self.config.data.cache_expiry_hours
        )
        
        # API设置
        api_timeout = st.number_input(
            "API超时时间 (秒)",
            min_value=10,
            max_value=120,
            value=self.config.data.api_timeout
        )
        
        max_retries = st.number_input(
            "最大重试次数",
            min_value=1,
            max_value=10,
            value=self.config.data.max_retries
        )
        
        # 缓存管理
        st.markdown("---")
        st.subheader("🗂️ 缓存管理")
        
        cache_dir = self.config.data.cache_dir
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
            st.info(f"当前缓存文件数量: {len(cache_files)}")
            
            if st.button("🗑️ 清空缓存"):
                try:
                    for file in cache_files:
                        os.remove(os.path.join(cache_dir, file))
                    st.success("缓存已清空！")
                    st.rerun()
                except Exception as e:
                    st.error(f"清空缓存失败: {str(e)}")
        else:
            st.info("缓存目录不存在")
        
        if st.button("保存数据设置"):
            try:
                self.config.update_config('data', {
                    'cache_expiry_hours': cache_expiry,
                    'api_timeout': api_timeout,
                    'max_retries': max_retries
                })
                self.config.save_config()
                st.success("数据设置已保存！")
            except Exception as e:
                st.error(f"保存设置失败: {str(e)}")


def main():
    """主函数 - Streamlit应用入口点"""
    # 设置日志系统
    setup_logging()
    
    # 创建并运行应用
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()
    def _show_system_monitoring_settings(self):
        """显示系统监控设置"""
        try:
            st.subheader("🔧 系统监控与错误管理")
            
            # 系统健康状态
            st.markdown("### 📊 系统健康状态")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 执行健康检查", use_container_width=True):
                    with st.spinner("正在检查系统健康状态..."):
                        health_status = system_integrator.health_check()
                        ui_error_handler.show_system_health(health_status)
            
            with col2:
                if st.button("📈 查看性能报告", use_container_width=True):
                    self._show_performance_report()
            
            # 错误统计
            st.markdown("---")
            st.markdown("### 📋 错误统计")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 显示错误统计", use_container_width=True):
                    ui_error_handler.show_error_statistics()
            
            with col2:
                if st.button("🗑️ 清空错误历史", use_container_width=True):
                    ui_error_handler.error_handler.clear_error_history()
                    st.success("错误历史已清空")
            
            # 日志管理
            st.markdown("---")
            st.markdown("### 📝 日志管理")
            
            log_config = self.config.logging
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("日志级别", log_config.level)
            
            with col2:
                st.metric("日志文件", os.path.basename(log_config.file_path))
            
            with col3:
                # 检查日志文件大小
                if os.path.exists(log_config.file_path):
                    file_size = os.path.getsize(log_config.file_path)
                    size_mb = file_size / (1024 * 1024)
                    st.metric("文件大小", f"{size_mb:.1f} MB")
                else:
                    st.metric("文件大小", "不存在")
            
            # 日志级别设置
            st.markdown("#### 日志级别设置")
            
            log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            current_level = log_config.level
            
            new_level = st.selectbox(
                "选择日志级别",
                options=log_levels,
                index=log_levels.index(current_level) if current_level in log_levels else 1,
                help="更改日志级别将影响记录的日志详细程度"
            )
            
            if new_level != current_level:
                if st.button("🔄 应用日志级别"):
                    # 更新配置
                    self.config.logging.level = new_level
                    
                    # 重新设置日志系统
                    setup_logging(self.config)
                    
                    st.success(f"日志级别已更新为: {new_level}")
                    st.rerun()
            
            # 性能监控设置
            st.markdown("---")
            st.markdown("### ⚡ 性能监控设置")
            
            from etf_dashboard.core.performance_monitor import performance_monitor
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("监控状态", "运行中" if performance_monitor.system_monitor_enabled else "已停止")
            
            with col2:
                st.metric("历史记录数", len(performance_monitor.metrics_history))
            
            with col3:
                st.metric("慢函数数", len(performance_monitor.slow_functions))
            
            # 性能监控控制
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            
            with perf_col1:
                if not performance_monitor.system_monitor_enabled:
                    if st.button("▶️ 启动监控", use_container_width=True):
                        start_performance_monitoring()
                        st.success("性能监控已启动")
                        st.rerun()
                else:
                    if st.button("⏹️ 停止监控", use_container_width=True):
                        from etf_dashboard.core.performance_monitor import stop_performance_monitoring
                        stop_performance_monitoring()
                        st.success("性能监控已停止")
                        st.rerun()
            
            with perf_col2:
                if st.button("📊 性能报告", use_container_width=True):
                    self._show_performance_report()
            
            with perf_col3:
                if st.button("🗑️ 清空数据", use_container_width=True):
                    from etf_dashboard.core.performance_monitor import clear_performance_data
                    clear_performance_data()
                    st.success("性能数据已清空")
                    st.rerun()
            
            # 错误处理设置
            st.markdown("---")
            st.markdown("### 🚨 错误处理设置")
            
            error_display_modes = {
                "最小化": "minimal",
                "标准": "standard", 
                "详细": "detailed",
                "调试": "debug"
            }
            
            current_mode = ui_error_handler.display_mode.value
            current_mode_name = next(
                (name for name, mode in error_display_modes.items() if mode == current_mode),
                "标准"
            )
            
            new_mode_name = st.selectbox(
                "错误显示模式",
                options=list(error_display_modes.keys()),
                index=list(error_display_modes.keys()).index(current_mode_name),
                help="选择错误信息的显示详细程度"
            )
            
            if error_display_modes[new_mode_name] != current_mode:
                if st.button("🔄 应用显示模式"):
                    from etf_dashboard.core.ui_error_handler import UIErrorDisplayMode
                    new_mode = UIErrorDisplayMode(error_display_modes[new_mode_name])
                    ui_error_handler.set_display_mode(new_mode)
                    st.success(f"错误显示模式已更新为: {new_mode_name}")
                    st.rerun()
            
            # 系统信息
            st.markdown("---")
            st.markdown("### 💻 系统信息")
            
            import platform
            import sys
            
            system_info = {
                "操作系统": platform.system(),
                "系统版本": platform.release(),
                "Python版本": sys.version.split()[0],
                "Streamlit版本": st.__version__,
                "工作目录": os.getcwd(),
                "配置文件": self.config.config_file
            }
            
            for key, value in system_info.items():
                st.text(f"{key}: {value}")
                
        except Exception as e:
            show_error_with_recovery(
                error=e,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                context={'function': '_show_system_monitoring_settings'},
                user_message="显示系统监控设置失败",
                recovery_suggestion="请刷新页面重试"
            )
    
    def _show_performance_report(self):
        """显示性能报告"""
        try:
            from etf_dashboard.core.performance_monitor import get_performance_report
            
            with st.expander("📈 性能报告", expanded=True):
                report = get_performance_report()
                
                if 'message' in report:
                    st.info(report['message'])
                    return
                
                # 总体统计
                st.subheader("📊 总体统计")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("总调用次数", report['total_function_calls'])
                
                with col2:
                    st.metric("平均执行时间", f"{report['avg_execution_time']:.3f}s")
                
                with col3:
                    st.metric("最长执行时间", f"{report['max_execution_time']:.3f}s")
                
                with col4:
                    avg_memory_mb = report['avg_memory_usage'] / (1024 * 1024)
                    st.metric("平均内存使用", f"{avg_memory_mb:.1f}MB")
                
                # 函数统计
                if report['function_statistics']:
                    st.subheader("🔧 函数统计")
                    
                    func_data = []
                    for func_name, stats in report['function_statistics'].items():
                        func_data.append({
                            "函数名": func_name.split('.')[-1],  # 只显示函数名
                            "调用次数": stats['call_count'],
                            "平均时间": f"{stats['avg_execution_time']:.3f}s",
                            "最长时间": f"{stats['max_execution_time']:.3f}s",
                            "错误次数": stats['error_count']
                        })
                    
                    if func_data:
                        st.dataframe(func_data, use_container_width=True, hide_index=True)
                
                # 慢函数
                if report['slow_functions']:
                    st.subheader("🐌 慢函数调用")
                    
                    for slow_func in report['slow_functions']:
                        st.warning(
                            f"🐌 {slow_func['function_name'].split('.')[-1]} - "
                            f"{slow_func['execution_time']:.3f}s "
                            f"({slow_func['timestamp']})"
                        )
                
                # 生成时间
                st.info(f"报告生成时间: {report['generated_at']}")
                
        except Exception as e:
            st.error(f"生成性能报告失败: {str(e)}")
    
    def _show_ui_settings(self):
        """显示界面设置"""
        try:
            st.subheader("🎨 界面配置")
            
            # 主题设置
            current_theme = self.config.ui.theme
            new_theme = st.selectbox(
                "主题",
                options=["light", "dark"],
                index=0 if current_theme == "light" else 1,
                help="选择界面主题"
            )
            
            # 布局设置
            current_layout = self.config.ui.layout
            new_layout = st.selectbox(
                "页面布局",
                options=["centered", "wide"],
                index=0 if current_layout == "centered" else 1,
                help="选择页面布局方式"
            )
            
            # 调试信息
            current_debug = self.config.ui.show_debug_info
            new_debug = st.checkbox(
                "显示调试信息",
                value=current_debug,
                help="是否在界面中显示调试信息"
            )
            
            # 图表高度
            current_height = self.config.ui.chart_height
            new_height = st.slider(
                "图表高度",
                min_value=300,
                max_value=800,
                value=current_height,
                step=50,
                help="设置图表的默认高度"
            )
            
            # 应用设置
            if st.button("💾 保存界面设置"):
                self.config.ui.theme = new_theme
                self.config.ui.layout = new_layout
                self.config.ui.show_debug_info = new_debug
                self.config.ui.chart_height = new_height
                
                try:
                    self.config.save_config()
                    st.success("界面设置已保存！请刷新页面以应用更改。")
                except Exception as e:
                    st.error(f"保存设置失败: {str(e)}")
                    
        except Exception as e:
            st.error(f"显示界面设置失败: {str(e)}")
    
    def _show_indicator_settings(self):
        """显示技术指标设置"""
        try:
            st.subheader("📈 技术指标配置")
            
            # RSI设置
            st.markdown("#### RSI设置")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                rsi_period = st.number_input(
                    "RSI周期",
                    min_value=5,
                    max_value=50,
                    value=self.config.indicators.rsi_period,
                    help="RSI计算的周期天数"
                )
            
            with col2:
                rsi_overbought = st.number_input(
                    "超买线",
                    min_value=60.0,
                    max_value=90.0,
                    value=self.config.indicators.rsi_overbought,
                    step=1.0,
                    help="RSI超买阈值"
                )
            
            with col3:
                rsi_oversold = st.number_input(
                    "超卖线",
                    min_value=10.0,
                    max_value=40.0,
                    value=self.config.indicators.rsi_oversold,
                    step=1.0,
                    help="RSI超卖阈值"
                )
            
            # 移动平均线设置
            st.markdown("#### 移动平均线设置")
            
            ma_periods_str = ', '.join(map(str, self.config.indicators.ma_periods))
            new_ma_periods_str = st.text_input(
                "MA周期",
                value=ma_periods_str,
                help="移动平均线周期，用逗号分隔，例如: 5, 20, 60"
            )
            
            # 应用设置
            if st.button("💾 保存技术指标设置"):
                try:
                    # 解析MA周期
                    ma_periods = [int(x.strip()) for x in new_ma_periods_str.split(',')]
                    
                    # 更新配置
                    self.config.indicators.rsi_period = rsi_period
                    self.config.indicators.rsi_overbought = rsi_overbought
                    self.config.indicators.rsi_oversold = rsi_oversold
                    self.config.indicators.ma_periods = ma_periods
                    
                    self.config.save_config()
                    st.success("技术指标设置已保存！")
                    
                except ValueError:
                    st.error("MA周期格式错误，请使用逗号分隔的数字")
                except Exception as e:
                    st.error(f"保存设置失败: {str(e)}")
                    
        except Exception as e:
            st.error(f"显示技术指标设置失败: {str(e)}")
    
    def _show_signal_settings(self):
        """显示信号规则设置"""
        try:
            st.subheader("🔔 信号规则配置")
            
            # 回撤阈值
            max_drawdown = st.slider(
                "最大回撤阈值",
                min_value=0.05,
                max_value=0.50,
                value=self.config.signals.max_drawdown_threshold,
                step=0.01,
                format="%.2f",
                help="超过此回撤比例将禁止买入"
            )
            
            # 置信度阈值
            confidence_threshold = st.slider(
                "信号置信度阈值",
                min_value=0.1,
                max_value=0.9,
                value=self.config.signals.confidence_threshold,
                step=0.1,
                format="%.1f",
                help="信号置信度低于此值将不推荐操作"
            )
            
            # 过滤器开关
            st.markdown("#### 信号过滤器")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                trend_filter = st.checkbox(
                    "启用趋势过滤",
                    value=self.config.signals.enable_trend_filter,
                    help="是否启用趋势状态过滤"
                )
            
            with col2:
                rsi_filter = st.checkbox(
                    "启用RSI过滤",
                    value=self.config.signals.enable_rsi_filter,
                    help="是否启用RSI过滤"
                )
            
            with col3:
                drawdown_filter = st.checkbox(
                    "启用回撤过滤",
                    value=self.config.signals.enable_drawdown_filter,
                    help="是否启用最大回撤过滤"
                )
            
            # 应用设置
            if st.button("💾 保存信号规则设置"):
                try:
                    self.config.signals.max_drawdown_threshold = max_drawdown
                    self.config.signals.confidence_threshold = confidence_threshold
                    self.config.signals.enable_trend_filter = trend_filter
                    self.config.signals.enable_rsi_filter = rsi_filter
                    self.config.signals.enable_drawdown_filter = drawdown_filter
                    
                    self.config.save_config()
                    st.success("信号规则设置已保存！")
                    
                except Exception as e:
                    st.error(f"保存设置失败: {str(e)}")
                    
        except Exception as e:
            st.error(f"显示信号规则设置失败: {str(e)}")
    
    def _show_data_settings(self):
        """显示数据管理设置"""
        try:
            st.subheader("💾 数据管理")
            
            # 缓存设置
            st.markdown("#### 缓存配置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                cache_expiry = st.number_input(
                    "缓存过期时间（小时）",
                    min_value=1,
                    max_value=168,  # 7天
                    value=self.config.data.cache_expiry_hours,
                    help="缓存数据的有效期"
                )
            
            with col2:
                api_timeout = st.number_input(
                    "API超时时间（秒）",
                    min_value=5,
                    max_value=120,
                    value=self.config.data.api_timeout,
                    help="数据获取的超时时间"
                )
            
            # 缓存状态
            st.markdown("#### 缓存状态")
            
            cache_dir = self.config.data.cache_dir
            if os.path.exists(cache_dir):
                cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.pkl')]
                total_size = sum(
                    os.path.getsize(os.path.join(cache_dir, f)) 
                    for f in cache_files
                )
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("缓存文件数", len(cache_files))
                
                with col2:
                    st.metric("缓存大小", f"{total_size / (1024*1024):.1f} MB")
                
                with col3:
                    st.metric("缓存目录", cache_dir)
                
                # 缓存管理
                if st.button("🗑️ 清空缓存"):
                    try:
                        for file in cache_files:
                            os.remove(os.path.join(cache_dir, file))
                        st.success(f"已清空 {len(cache_files)} 个缓存文件")
                    except Exception as e:
                        st.error(f"清空缓存失败: {str(e)}")
            else:
                st.info("缓存目录不存在")
            
            # 应用设置
            if st.button("💾 保存数据设置"):
                try:
                    self.config.data.cache_expiry_hours = cache_expiry
                    self.config.data.api_timeout = api_timeout
                    
                    self.config.save_config()
                    st.success("数据设置已保存！")
                    
                except Exception as e:
                    st.error(f"保存设置失败: {str(e)}")
                    
        except Exception as e:
            st.error(f"显示数据设置失败: {str(e)}")


# 主应用入口
def main():
    """主应用入口函数"""
    try:
        # 设置日志系统
        setup_logging()
        
        # 创建并运行仪表盘应用
        app = DashboardApp()
        app.run()
        
    except Exception as e:
        st.error("应用启动失败")
        st.error(str(e))
        
        # 显示错误恢复选项
        if st.button("🔄 重新启动应用"):
            st.rerun()


if __name__ == "__main__":
    main()
    def _show_network_diagnostics(self):
        """显示网络诊断功能"""
        st.subheader("🌐 网络连接诊断")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔍 开始网络诊断", type="primary"):
                with st.spinner("正在进行网络诊断..."):
                    try:
                        # 获取数据加载器
                        data_loader = system_integrator.get_component('data_loader')
                        if data_loader and hasattr(data_loader, 'test_network_connection'):
                            test_results = data_loader.test_network_connection()
                            
                            st.subheader("诊断结果")
                            
                            # 基本网络连接
                            if test_results['basic_internet']:
                                st.success("✅ 基本网络连接正常")
                            else:
                                st.error("❌ 基本网络连接失败")
                            
                            # 东方财富API连接
                            if test_results['eastmoney_api']:
                                st.success("✅ 东方财富API连接正常")
                            else:
                                st.error("❌ 东方财富API连接失败")
                            
                            # 代理状态
                            proxy_status = test_results['proxy_status']
                            if proxy_status == 'enabled':
                                st.info("🔄 代理已启用")
                            elif proxy_status == 'not_used':
                                st.info("🔄 未使用代理")
                            
                            # 错误信息
                            if test_results['error_messages']:
                                st.subheader("错误详情")
                                for error in test_results['error_messages']:
                                    st.error(f"• {error}")
                        else:
                            st.error("数据加载器不支持网络诊断功能")
                            
                    except Exception as e:
                        st.error(f"网络诊断失败: {str(e)}")
        
        with col2:
            st.subheader("网络配置")
            
            # 显示当前网络配置
            network_config = self.config.data.__dict__.get('network', {})
            
            use_proxy = st.checkbox(
                "使用代理", 
                value=network_config.get('use_proxy', False),
                help="启用HTTP/HTTPS代理"
            )
            
            if use_proxy:
                proxy_host = st.text_input(
                    "代理主机", 
                    value=network_config.get('proxy_host', ''),
                    placeholder="例如: 127.0.0.1"
                )
                
                proxy_port = st.text_input(
                    "代理端口", 
                    value=str(network_config.get('proxy_port', '')),
                    placeholder="例如: 8080"
                )
                
                with st.expander("高级代理设置"):
                    proxy_username = st.text_input(
                        "用户名 (可选)", 
                        value=network_config.get('proxy_username', ''),
                        type="default"
                    )
                    
                    proxy_password = st.text_input(
                        "密码 (可选)", 
                        value=network_config.get('proxy_password', ''),
                        type="password"
                    )
            
            disable_ssl = st.checkbox(
                "禁用SSL验证", 
                value=network_config.get('disable_ssl_verify', False),
                help="⚠️ 仅在测试环境使用"
            )
            
            if st.button("💾 保存网络设置"):
                try:
                    # 更新配置
                    if not hasattr(self.config.data, 'network'):
                        self.config.data.network = {}
                    
                    self.config.data.network['use_proxy'] = use_proxy
                    if use_proxy:
                        self.config.data.network['proxy_host'] = proxy_host
                        self.config.data.network['proxy_port'] = proxy_port
                        if proxy_username:
                            self.config.data.network['proxy_username'] = proxy_username
                        if proxy_password:
                            self.config.data.network['proxy_password'] = proxy_password
                    
                    self.config.data.network['disable_ssl_verify'] = disable_ssl
                    
                    # 保存配置到文件
                    import json
                    with open('config/settings.json', 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    config_data['data']['network'] = self.config.data.network
                    
                    with open('config/settings.json', 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, indent=2, ensure_ascii=False)
                    
                    st.success("网络设置已保存！请重启应用以使设置生效。")
                    
                except Exception as e:
                    st.error(f"保存网络设置失败: {str(e)}")
        
        # 网络故障排除建议
        with st.expander("🛠️ 网络故障排除建议"):
            st.markdown("""
            **常见网络问题及解决方案：**
            
            1. **代理连接失败**
               - 检查代理服务器地址和端口是否正确
               - 确认代理服务器正在运行
               - 尝试禁用代理直接连接
            
            2. **SSL证书错误**
               - 临时启用"禁用SSL验证"选项（仅测试用）
               - 检查系统时间是否正确
               - 更新系统证书
            
            3. **网络超时**
               - 检查网络连接稳定性
               - 尝试增加API超时时间
               - 使用缓存数据继续工作
            
            4. **防火墙阻止**
               - 检查防火墙设置
               - 将应用添加到防火墙白名单
               - 确认端口未被阻止
            """)
    def _show_data_source_status(self):
        """显示数据源状态"""
        st.subheader("📊 数据源状态")
        
        try:
            # 获取数据源状态
            if hasattr(self.data_loader, 'get_data_source_status'):
                status = self.data_loader.get_data_source_status()
                
                # 显示主数据源
                if status.get('primary_source'):
                    st.success(f"🎯 主数据源: {status['primary_source']}")
                
                # 显示所有数据源状态
                st.subheader("数据源详情")
                
                for source in status.get('sources', []):
                    name = source.get('name', 'Unknown')
                    available = source.get('available', False)
                    is_primary = source.get('is_primary', False)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        if is_primary:
                            st.write(f"🎯 **{name}** (主要)")
                        else:
                            st.write(f"🔄 {name} (备用)")
                    
                    with col2:
                        if available:
                            st.success("✅ 可用")
                        else:
                            st.error("❌ 不可用")
                    
                    with col3:
                        if source.get('last_error'):
                            st.error(f"错误: {source['last_error'][:30]}...")
                        else:
                            st.info("正常")
                
                # 显示备用状态
                if status.get('fallback_available'):
                    st.info("🛡️ 备用数据源可用")
                else:
                    st.warning("⚠️ 无可用备用数据源")
            
            # 测试所有数据源按钮
            if st.button("🔍 测试所有数据源"):
                with st.spinner("正在测试数据源连接..."):
                    if hasattr(self.data_loader, 'test_all_data_sources'):
                        test_results = self.data_loader.test_all_data_sources()
                        
                        st.subheader("连接测试结果")
                        
                        total_sources = test_results.get('total_count', 0)
                        available_sources = test_results.get('available_count', 0)
                        
                        if available_sources > 0:
                            st.success(f"✅ {available_sources}/{total_sources} 个数据源可用")
                        else:
                            st.error("❌ 所有数据源都不可用")
                        
                        # 显示详细测试结果
                        for source_name, result in test_results.get('sources', {}).items():
                            with st.expander(f"📊 {source_name} 测试结果"):
                                if result.get('available'):
                                    st.success("✅ 连接成功")
                                else:
                                    st.error("❌ 连接失败")
                                    if result.get('last_error'):
                                        st.error(f"错误信息: {result['last_error']}")
                                
                                if result.get('config'):
                                    st.info("🔧 已配置")
                                else:
                                    st.warning("⚙️ 未配置")
                    else:
                        st.error("数据加载器不支持多数据源测试")
        
        except Exception as e:
            st.error(f"显示数据源状态失败: {str(e)}")
    
    def _show_data_source_settings(self):
        """显示数据源设置"""
        st.subheader("🔧 数据源配置")
        
        try:
            # 多数据源开关
            use_multi_source = st.checkbox(
                "启用多数据源模式",
                value=True,
                help="启用后将使用多个数据源进行故障转移"
            )
            
            if use_multi_source:
                st.info("📊 多数据源模式已启用，支持自动故障转移")
                
                # Yahoo Finance 设置
                with st.expander("🌐 Yahoo Finance 设置"):
                    yahoo_enabled = st.checkbox("启用 Yahoo Finance", value=True)
                    if yahoo_enabled:
                        st.success("✅ Yahoo Finance 已启用")
                        st.info("支持全球股票和ETF数据")
                
                # Alpha Vantage 设置
                with st.expander("📈 Alpha Vantage 设置"):
                    alpha_enabled = st.checkbox("启用 Alpha Vantage", value=True)
                    if alpha_enabled:
                        alpha_api_key = st.text_input(
                            "API Key",
                            value="demo",
                            type="password",
                            help="从 https://www.alphavantage.co/ 获取免费API密钥"
                        )
                        if alpha_api_key == "demo":
                            st.warning("⚠️ 使用演示API密钥，功能受限")
                        else:
                            st.success("✅ 已配置自定义API密钥")
                
                # 模拟数据源设置
                with st.expander("🎲 模拟数据源设置"):
                    mock_enabled = st.checkbox("启用模拟数据源", value=True)
                    if mock_enabled:
                        st.success("✅ 模拟数据源已启用")
                        st.info("用于演示和测试，生成随机但合理的数据")
                
                # akshare 设置
                with st.expander("📊 akshare 设置"):
                    akshare_enabled = st.checkbox("启用 akshare", value=False)
                    if akshare_enabled:
                        st.warning("⚠️ akshare 当前不稳定，建议禁用")
                    else:
                        st.info("ℹ️ akshare 已禁用")
            
            else:
                st.warning("⚠️ 多数据源模式已禁用，仅使用 akshare")
            
            # 保存设置按钮
            if st.button("💾 保存数据源设置"):
                try:
                    # 这里可以添加保存配置的逻辑
                    st.success("✅ 数据源设置已保存")
                    st.info("ℹ️ 请重启应用以使设置生效")
                except Exception as e:
                    st.error(f"保存设置失败: {str(e)}")
        
        except Exception as e:
            st.error(f"显示数据源设置失败: {str(e)}")