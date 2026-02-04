"""
数据加载器模块

负责从外部数据源（如akshare）获取ETF数据，包括数据获取、格式转换和错误处理。
实现数据缓存机制以减少API调用频率。
现在支持多数据源故障转移机制。
"""

import logging
import re
import time
import os
import requests
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

from ..models import ETFData, PriceData, ETFList
from .cache import DataCache
from .validator import DataValidator
from .multi_source_loader import MultiSourceDataLoader


class DataLoader:
    """ETF数据获取和管理组件"""
    
    def __init__(self, cache_dir: str = "data/cache", config: dict = None):
        """
        初始化数据加载器
        
        Args:
            cache_dir: 缓存目录路径
            config: 配置字典，包含网络设置
        """
        self.logger = logging.getLogger(__name__)
        self.cache = DataCache(cache_dir)
        self.validator = DataValidator()
        self.config = config or {}
        
        # 配置网络设置
        self._setup_network_config()
        
        # 初始化多数据源加载器
        data_sources_config = self.config.get('data_sources', {})
        if data_sources_config.get('use_multi_source', True):
            self.multi_source_loader = MultiSourceDataLoader(cache_dir, data_sources_config)
            self.use_multi_source = True
            self.logger.info("启用多数据源模式")
        else:
            self.multi_source_loader = None
            self.use_multi_source = False
            self.logger.info("使用传统akshare模式")
        
        # ETF代码格式正则表达式
        self.a_stock_pattern = re.compile(r'^\d{6}$')  # A股ETF: 6位数字
        self.us_stock_pattern = re.compile(r'^[A-Z]{2,5}$')  # 美股ETF: 2-5位字母
        
        # 重试配置
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
    
    def _setup_network_config(self):
        """配置网络设置"""
        network_config = self.config.get('network', {})
        
        # 设置代理
        if network_config.get('use_proxy', False):
            proxy_host = network_config.get('proxy_host')
            proxy_port = network_config.get('proxy_port')
            proxy_username = network_config.get('proxy_username')
            proxy_password = network_config.get('proxy_password')
            
            if proxy_host and proxy_port:
                if proxy_username and proxy_password:
                    proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
                else:
                    proxy_url = f"http://{proxy_host}:{proxy_port}"
                
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                self.logger.info(f"设置代理: {proxy_host}:{proxy_port}")
        else:
            # 清除代理设置
            for proxy_env in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                if proxy_env in os.environ:
                    del os.environ[proxy_env]
            self.logger.info("已清除代理设置")
        
        # 设置 User-Agent
        user_agent = network_config.get('user_agent')
        if user_agent:
            # 为 requests 设置默认 headers
            requests.adapters.DEFAULT_RETRIES = 3
            
        # 设置 SSL 验证
        if network_config.get('disable_ssl_verify', False):
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.logger.warning("已禁用SSL证书验证")
    
    def test_network_connection(self) -> Dict[str, any]:
        """测试网络连接"""
        test_results = {
            'basic_internet': False,
            'eastmoney_api': False,
            'proxy_status': 'not_used',
            'error_messages': []
        }
        
        try:
            # 测试基本网络连接
            response = requests.get('https://www.baidu.com', timeout=10)
            if response.status_code == 200:
                test_results['basic_internet'] = True
                self.logger.info("基本网络连接正常")
            
        except Exception as e:
            test_results['error_messages'].append(f"基本网络连接失败: {str(e)}")
            self.logger.error(f"基本网络连接失败: {str(e)}")
        
        try:
            # 测试东方财富API连接
            test_url = "https://88.push2.eastmoney.com/api/qt/clist/get"
            response = requests.get(test_url, timeout=10)
            if response.status_code == 200:
                test_results['eastmoney_api'] = True
                self.logger.info("东方财富API连接正常")
            
        except Exception as e:
            test_results['error_messages'].append(f"东方财富API连接失败: {str(e)}")
            self.logger.error(f"东方财富API连接失败: {str(e)}")
        
        # 检查代理状态
        if 'HTTP_PROXY' in os.environ or 'HTTPS_PROXY' in os.environ:
            test_results['proxy_status'] = 'enabled'
        
        return test_results
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[PriceData]:
        """
        获取ETF历史数据
        
        Args:
            symbol: ETF代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            包含OHLCV数据的DataFrame，如果获取失败返回None
        """
        try:
            # 优先使用多数据源加载器
            if self.use_multi_source and self.multi_source_loader:
                self.logger.info(f"使用多数据源获取数据: {symbol}")
                return self.multi_source_loader.get_etf_data(symbol, start_date, end_date)
            
            # 回退到传统akshare方式
            self.logger.info(f"使用akshare获取数据: {symbol}")
            return self._get_etf_data_akshare(symbol, start_date, end_date)
            
        except Exception as e:
            self.logger.error(f"获取ETF数据失败 {symbol}: {str(e)}")
            return None
    
    def _get_etf_data_akshare(self, symbol: str, start_date: str, end_date: str) -> Optional[PriceData]:
        """
        使用akshare获取ETF历史数据（原有逻辑）
        """
        try:
            # 验证ETF代码格式
            if not self.validate_symbol(symbol):
                self.logger.error(f"无效的ETF代码格式: {symbol}")
                return None
            
            # 尝试从缓存加载数据
            cached_data = self.load_cached_data(symbol)
            if cached_data is not None and self._is_cache_valid(cached_data, start_date, end_date):
                self.logger.info(f"从缓存加载ETF数据: {symbol}")
                return self._filter_date_range(cached_data, start_date, end_date)
            
            # 从API获取数据（带重试机制）
            self.logger.info(f"从API获取ETF数据: {symbol}")
            data = self._fetch_from_api_with_retry(symbol, start_date, end_date)
            
            if data is not None:
                # 验证和格式化数据
                validated_data = self.validator.validate_price_data(data)
                if validated_data is not None:
                    # 缓存数据
                    self.cache_data(symbol, validated_data)
                    return validated_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取ETF数据失败 {symbol}: {str(e)}")
            return None
    
    def get_etf_list(self, market: str = "A") -> ETFList:
        """
        获取ETF列表
        
        Args:
            market: 市场类型 ("A" for A股, "US" for 美股)
            
        Returns:
            ETF列表，每个元素包含symbol和name
        """
        try:
            # 优先使用多数据源加载器
            if self.use_multi_source and self.multi_source_loader:
                self.logger.info(f"使用多数据源获取ETF列表: {market}")
                result = self.multi_source_loader.get_etf_list(market)
                if result:
                    # 转换格式以保持兼容性
                    formatted_result = []
                    for etf in result:
                        formatted_result.append({
                            'symbol': str(etf.get('代码', etf.get('symbol', ''))),
                            'name': str(etf.get('名称', etf.get('name', '')))
                        })
                    return formatted_result
            
            # 回退到传统akshare方式
            self.logger.info(f"使用akshare获取ETF列表: {market}")
            return self._get_etf_list_akshare(market)
            
        except Exception as e:
            self.logger.error(f"获取ETF列表失败: {str(e)}")
            return []
    
    def _get_etf_list_akshare(self, market: str = "A") -> ETFList:
        """
        使用akshare获取ETF列表（原有逻辑）
        """
        try:
            if market == "A":
                # 获取A股ETF列表（带重试机制）
                for attempt in range(self.max_retries):
                    try:
                        etf_list = ak.fund_etf_spot_em()
                        if etf_list is not None and not etf_list.empty:
                            result = []
                            for _, row in etf_list.iterrows():
                                result.append({
                                    'symbol': str(row['代码']),
                                    'name': str(row['名称'])
                                })
                            self.logger.info(f"获取到 {len(result)} 个A股ETF")
                            return result
                        else:
                            self.logger.warning("API返回空的ETF列表")
                            
                    except Exception as e:
                        self.logger.warning(f"获取ETF列表失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay)
                        else:
                            raise e
            else:
                self.logger.warning(f"暂不支持市场类型: {market}")
                
        except Exception as e:
            self.logger.error(f"获取ETF列表失败: {str(e)}")
        
        return []
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        验证ETF代码格式
        
        Args:
            symbol: ETF代码
            
        Returns:
            是否为有效格式
        """
        if not symbol or not isinstance(symbol, str):
            return False
        
        symbol = symbol.strip().upper()
        
        # 检查A股ETF格式 (6位数字)
        if self.a_stock_pattern.match(symbol):
            return True
        
        # 检查美股ETF格式 (2-5位字母)
        if self.us_stock_pattern.match(symbol):
            return True
        
        return False
    
    def cache_data(self, symbol: str, data: PriceData) -> None:
        """
        缓存ETF数据
        
        Args:
            symbol: ETF代码
            data: 价格数据
        """
        try:
            self.cache.save(symbol, data)
            self.logger.debug(f"缓存ETF数据: {symbol}")
        except Exception as e:
            self.logger.error(f"缓存数据失败 {symbol}: {str(e)}")
    
    def load_cached_data(self, symbol: str) -> Optional[PriceData]:
        """
        加载缓存的ETF数据
        
        Args:
            symbol: ETF代码
            
        Returns:
            缓存的价格数据，如果不存在返回None
        """
        try:
            return self.cache.load(symbol)
        except Exception as e:
            self.logger.error(f"加载缓存数据失败 {symbol}: {str(e)}")
            return None
    
    def _fetch_from_api_with_retry(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从API获取数据（带重试机制）
        
        Args:
            symbol: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            原始数据DataFrame
        """
        for attempt in range(self.max_retries):
            try:
                data = self._fetch_from_api(symbol, start_date, end_date)
                if data is not None:
                    return data
                else:
                    self.logger.warning(f"API返回空数据 (尝试 {attempt + 1}/{self.max_retries}): {symbol}")
                    
            except Exception as e:
                self.logger.warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}) {symbol}: {str(e)}")
                
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))  # 递增延迟
        
        self.logger.error(f"所有重试都失败，无法获取数据: {symbol}")
        return None
    
    def _fetch_from_api(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从API获取数据
        
        Args:
            symbol: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            原始数据DataFrame
        """
        try:
            # 根据代码格式选择API
            if self.a_stock_pattern.match(symbol):
                # A股ETF数据
                data = ak.fund_etf_hist_em(
                    symbol=symbol, 
                    period="daily", 
                    start_date=start_date.replace('-', ''), 
                    end_date=end_date.replace('-', '')
                )
            else:
                # 美股ETF数据 (暂时使用A股API作为示例)
                self.logger.warning(f"美股ETF数据获取暂未实现: {symbol}")
                return None
            
            if data is not None and not data.empty:
                self.logger.debug(f"成功获取 {len(data)} 条数据: {symbol}")
                return data
            else:
                self.logger.warning(f"API返回空数据: {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"API调用失败 {symbol}: {str(e)}")
            return None
    
    def _is_cache_valid(self, cached_data: PriceData, start_date: str, end_date: str) -> bool:
        """
        检查缓存数据是否有效
        
        Args:
            cached_data: 缓存的数据
            start_date: 请求的开始日期
            end_date: 请求的结束日期
            
        Returns:
            缓存是否有效
        """
        if cached_data is None or cached_data.empty:
            return False
        
        try:
            # 检查日期范围覆盖
            data_start = cached_data.index.min()
            data_end = cached_data.index.max()
            
            req_start = pd.to_datetime(start_date)
            req_end = pd.to_datetime(end_date)
            
            # 缓存数据必须覆盖请求的日期范围
            if data_start <= req_start and data_end >= req_end:
                # 检查数据是否过期 (1天)
                now = datetime.now()
                if (now - data_end).days <= 1:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"缓存有效性检查失败: {str(e)}")
            return False
    
    def _filter_date_range(self, data: PriceData, start_date: str, end_date: str) -> PriceData:
        """
        过滤数据到指定日期范围
        
        Args:
            data: 原始数据
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            过滤后的数据
        """
        try:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            return data.loc[start:end]
        except Exception as e:
            self.logger.error(f"日期范围过滤失败: {str(e)}")
            return data
    def get_data_source_status(self) -> Dict[str, Any]:
        """获取数据源状态信息"""
        if self.use_multi_source and self.multi_source_loader:
            return self.multi_source_loader.get_source_status()
        else:
            return {
                'sources': [{'name': 'akshare', 'available': True, 'is_primary': True}],
                'primary_source': 'akshare',
                'fallback_available': False
            }
    
    def test_all_data_sources(self) -> Dict[str, Any]:
        """测试所有数据源连接"""
        if self.use_multi_source and self.multi_source_loader:
            return self.multi_source_loader.test_all_sources()
        else:
            # 测试akshare连接
            try:
                import akshare as ak
                # 简单测试
                test_data = ak.fund_etf_spot_em()
                is_available = test_data is not None and not test_data.empty
            except Exception as e:
                is_available = False
            
            return {
                'timestamp': datetime.now().isoformat(),
                'sources': {
                    'akshare': {
                        'available': is_available,
                        'last_error': None if is_available else 'Connection test failed',
                        'config': True
                    }
                },
                'available_count': 1 if is_available else 0,
                'total_count': 1
            }