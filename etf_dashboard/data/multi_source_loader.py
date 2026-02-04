"""
多数据源加载器

支持多个数据源的ETF数据获取，包括备用数据源和故障转移机制。
当主数据源不可用时，自动切换到备用数据源。
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
import json
import time
import random

from ..models import ETFData, PriceData, ETFList
from .cache import DataCache
from .validator import DataValidator


class DataSourceInterface:
    """数据源接口基类"""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.is_available = True
        self.last_error = None
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取ETF历史数据"""
        raise NotImplementedError
    
    def get_etf_list(self, market: str = "A") -> Optional[List[Dict[str, Any]]]:
        """获取ETF列表"""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """测试数据源连接"""
        raise NotImplementedError


class YahooFinanceSource(DataSourceInterface):
    """Yahoo Finance数据源"""
    
    def __init__(self, config: dict = None):
        super().__init__("yahoo_finance", config)
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从Yahoo Finance获取ETF数据"""
        try:
            # 转换日期格式
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
            
            # 构建请求URL
            yahoo_symbol = self._convert_symbol_to_yahoo(symbol)
            url = f"{self.base_url}/{yahoo_symbol}"
            
            params = {
                'period1': start_timestamp,
                'period2': end_timestamp,
                'interval': '1d',
                'includePrePost': 'true',
                'events': 'div%2Csplit'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' not in data or not data['chart']['result']:
                self.logger.warning(f"Yahoo Finance返回空数据: {symbol}")
                return None
            
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            
            # 构建DataFrame
            df = pd.DataFrame({
                'date': [datetime.fromtimestamp(ts) for ts in timestamps],
                'open': quotes['open'],
                'high': quotes['high'],
                'low': quotes['low'],
                'close': quotes['close'],
                'volume': quotes['volume']
            })
            
            # 清理数据
            df = df.dropna()
            df['date'] = pd.to_datetime(df['date'])
            # 不要立即设置索引，让验证器来处理
            
            self.logger.info(f"Yahoo Finance成功获取 {len(df)} 条数据: {symbol}")
            return df
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Yahoo Finance获取数据失败 {symbol}: {str(e)}")
            return None
    
    def get_etf_list(self, market: str = "A") -> Optional[List[Dict[str, Any]]]:
        """获取ETF列表（模拟数据）"""
        try:
            # 常见的中国ETF列表
            if market == "A":
                etf_list = [
                    {'代码': '159919', '名称': '沪深300ETF', '最新价': 4.85, '涨跌幅': 0.02},
                    {'代码': '510300', '名称': '沪深300ETF', '最新价': 4.86, '涨跌幅': 0.01},
                    {'代码': '159915', '名称': '创业板ETF', '最新价': 2.45, '涨跌幅': -0.01},
                    {'代码': '510500', '名称': '中证500ETF', '最新价': 6.78, '涨跌幅': 0.03},
                    {'代码': '159949', '名称': '创业板50ETF', '最新价': 1.23, '涨跌幅': -0.02},
                    {'代码': '512100', '名称': '中证1000ETF', '最新价': 3.45, '涨跌幅': 0.01},
                    {'代码': '159928', '名称': '消费ETF', '最新价': 2.89, '涨跌幅': 0.02},
                    {'代码': '512880', '名称': '证券ETF', '最新价': 0.98, '涨跌幅': -0.03},
                    {'代码': '159995', '名称': '芯片ETF', '最新价': 1.67, '涨跌幅': 0.04},
                    {'代码': '515050', '名称': '5G ETF', '最新价': 0.87, '涨跌幅': -0.01}
                ]
            else:
                # 美股ETF列表
                etf_list = [
                    {'代码': 'SPY', '名称': 'SPDR S&P 500 ETF', '最新价': 445.67, '涨跌幅': 0.01},
                    {'代码': 'QQQ', '名称': 'Invesco QQQ ETF', '最新价': 378.23, '涨跌幅': 0.02},
                    {'代码': 'IWM', '名称': 'iShares Russell 2000 ETF', '最新价': 198.45, '涨跌幅': -0.01},
                    {'代码': 'VTI', '名称': 'Vanguard Total Stock Market ETF', '最新价': 234.56, '涨跌幅': 0.01}
                ]
            
            return etf_list
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Yahoo Finance获取ETF列表失败: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """测试Yahoo Finance连接"""
        try:
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {'q': 'SPY', 'quotesCount': 1}
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _convert_symbol_to_yahoo(self, symbol: str) -> str:
        """转换股票代码为Yahoo Finance格式"""
        # A股ETF需要添加后缀
        if symbol.isdigit() and len(symbol) == 6:
            if symbol.startswith(('51', '15')):
                return f"{symbol}.SS"  # 上海
            elif symbol.startswith('16'):
                return f"{symbol}.SZ"  # 深圳
        return symbol


class AlphaVantageSource(DataSourceInterface):
    """Alpha Vantage数据源"""
    
    def __init__(self, config: dict = None):
        super().__init__("alpha_vantage", config)
        self.api_key = config.get('api_key', 'demo') if config else 'demo'
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从Alpha Vantage获取ETF数据"""
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': self.api_key,
                'outputsize': 'full'
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage错误: {data['Error Message']}")
                return None
            
            if 'Time Series (Daily)' not in data:
                self.logger.warning(f"Alpha Vantage返回格式异常: {symbol}")
                return None
            
            time_series = data['Time Series (Daily)']
            
            # 构建DataFrame
            df_data = []
            for date_str, values in time_series.items():
                df_data.append({
                    'date': pd.to_datetime(date_str),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume'])
                })
            
            df = pd.DataFrame(df_data)
            # 不要立即设置索引，让验证器来处理
            df = df.sort_values('date')
            
            # 过滤日期范围
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
            
            self.logger.info(f"Alpha Vantage成功获取 {len(df)} 条数据: {symbol}")
            return df
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Alpha Vantage获取数据失败 {symbol}: {str(e)}")
            return None
    
    def get_etf_list(self, market: str = "A") -> Optional[List[Dict[str, Any]]]:
        """获取ETF列表（使用搜索功能）"""
        # Alpha Vantage的搜索功能有限，返回预定义列表
        return YahooFinanceSource().get_etf_list(market)
    
    def test_connection(self) -> bool:
        """测试Alpha Vantage连接"""
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': 'SPY',
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            return response.status_code == 200
        except:
            return False


class MockDataSource(DataSourceInterface):
    """模拟数据源（用于测试和演示）"""
    
    def __init__(self, config: dict = None):
        super().__init__("mock_data", config)
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """生成模拟ETF数据"""
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # 生成日期范围
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
            # 只保留工作日
            date_range = date_range[date_range.weekday < 5]
            
            if len(date_range) == 0:
                return None
            
            # 生成模拟价格数据
            np.random.seed(hash(symbol) % 2**32)  # 使用symbol作为种子，确保一致性
            
            # 基础价格
            base_price = 5.0 + (hash(symbol) % 100) / 10.0
            
            # 生成价格序列
            returns = np.random.normal(0.001, 0.02, len(date_range))  # 日收益率
            prices = [base_price]
            
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(max(new_price, 0.1))  # 确保价格为正
            
            # 生成OHLC数据
            df_data = []
            for i, date in enumerate(date_range):
                close_price = prices[i]
                
                # 生成日内波动
                daily_volatility = abs(np.random.normal(0, 0.01))
                high_price = close_price * (1 + daily_volatility)
                low_price = close_price * (1 - daily_volatility)
                
                # 开盘价基于前一日收盘价
                if i == 0:
                    open_price = close_price
                else:
                    gap = np.random.normal(0, 0.005)
                    open_price = prices[i-1] * (1 + gap)
                
                # 确保价格逻辑正确
                high_price = max(high_price, open_price, close_price)
                low_price = min(low_price, open_price, close_price)
                
                # 生成成交量
                volume = int(np.random.uniform(1000000, 10000000))
                
                df_data.append({
                    'date': date,
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume
                })
            
            df = pd.DataFrame(df_data)
            # 不要立即设置索引，让验证器来处理
            
            self.logger.info(f"模拟数据源成功生成 {len(df)} 条数据: {symbol}")
            return df
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"模拟数据源生成数据失败 {symbol}: {str(e)}")
            return None
    
    def get_etf_list(self, market: str = "A") -> Optional[List[Dict[str, Any]]]:
        """生成模拟ETF列表"""
        try:
            if market == "A":
                etf_list = [
                    {'代码': '159919', '名称': '沪深300ETF', '最新价': 4.85, '涨跌幅': 0.02},
                    {'代码': '510300', '名称': '沪深300ETF', '最新价': 4.86, '涨跌幅': 0.01},
                    {'代码': '159915', '名称': '创业板ETF', '最新价': 2.45, '涨跌幅': -0.01},
                    {'代码': '510500', '名称': '中证500ETF', '最新价': 6.78, '涨跌幅': 0.03},
                    {'代码': '159949', '名称': '创业板50ETF', '最新价': 1.23, '涨跌幅': -0.02},
                    {'代码': '512100', '名称': '中证1000ETF', '最新价': 3.45, '涨跌幅': 0.01},
                    {'代码': '159928', '名称': '消费ETF', '最新价': 2.89, '涨跌幅': 0.02},
                    {'代码': '512880', '名称': '证券ETF', '最新价': 0.98, '涨跌幅': -0.03},
                    {'代码': '159995', '名称': '芯片ETF', '最新价': 1.67, '涨跌幅': 0.04},
                    {'代码': '515050', '名称': '5G ETF', '最新价': 0.87, '涨跌幅': -0.01}
                ]
            else:
                etf_list = [
                    {'代码': 'SPY', '名称': 'SPDR S&P 500 ETF', '最新价': 445.67, '涨跌幅': 0.01},
                    {'代码': 'QQQ', '名称': 'Invesco QQQ ETF', '最新价': 378.23, '涨跌幅': 0.02},
                    {'代码': 'IWM', '名称': 'iShares Russell 2000 ETF', '最新价': 198.45, '涨跌幅': -0.01},
                    {'代码': 'VTI', '名称': 'Vanguard Total Stock Market ETF', '最新价': 234.56, '涨跌幅': 0.01}
                ]
            
            # 添加随机波动
            for etf in etf_list:
                price_change = np.random.uniform(-0.05, 0.05)
                etf['最新价'] = round(etf['最新价'] * (1 + price_change), 2)
                etf['涨跌幅'] = round(price_change, 4)
            
            return etf_list
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"模拟数据源生成ETF列表失败: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """模拟数据源总是可用"""
        return True


class MultiSourceDataLoader:
    """多数据源数据加载器"""
    
    def __init__(self, cache_dir: str = "data/cache", config: dict = None):
        self.logger = logging.getLogger(__name__)
        self.cache = DataCache(cache_dir)
        self.validator = DataValidator()
        self.config = config or {}
        
        # 初始化数据源
        self.data_sources = []
        self._initialize_data_sources()
        
        # 重试配置
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
    
    def _initialize_data_sources(self):
        """初始化所有数据源"""
        try:
            # 1. Yahoo Finance (主要数据源)
            yahoo_config = self.config.get('yahoo_finance', {})
            self.data_sources.append(YahooFinanceSource(yahoo_config))
            
            # 2. Alpha Vantage (备用数据源)
            alpha_config = self.config.get('alpha_vantage', {})
            self.data_sources.append(AlphaVantageSource(alpha_config))
            
            # 3. 模拟数据源 (最后备用)
            mock_config = self.config.get('mock_data', {})
            self.data_sources.append(MockDataSource(mock_config))
            
            self.logger.info(f"初始化了 {len(self.data_sources)} 个数据源")
            
        except Exception as e:
            self.logger.error(f"初始化数据源失败: {str(e)}")
            # 至少保证有模拟数据源可用
            self.data_sources = [MockDataSource()]
    
    def get_etf_data(self, symbol: str, start_date: str, end_date: str) -> Optional[PriceData]:
        """获取ETF历史数据（多数据源故障转移）"""
        # 首先尝试从缓存获取
        cache_key = f"etf_data_{symbol}_{start_date}_{end_date}"
        cached_data = self.cache.load(cache_key)
        
        if cached_data is not None and self._is_cache_valid(cached_data, start_date, end_date):
            self.logger.info(f"从缓存获取数据: {symbol}")
            return cached_data
        
        # 尝试从各个数据源获取数据
        for source in self.data_sources:
            if not source.is_available:
                continue
            
            self.logger.info(f"尝试从 {source.name} 获取数据: {symbol}")
            
            for attempt in range(self.max_retries):
                try:
                    raw_data = source.get_etf_data(symbol, start_date, end_date)
                    
                    if raw_data is not None and not raw_data.empty:
                        # 验证数据
                        validated_data = self.validator.validate_price_data(raw_data)
                        
                        if validated_data is not None:
                            # 缓存数据
                            self.cache.save(cache_key, validated_data)
                            
                            self.logger.info(f"成功从 {source.name} 获取数据: {symbol}")
                            return validated_data
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
                except Exception as e:
                    self.logger.warning(f"{source.name} 获取数据失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    source.last_error = str(e)
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
            
            # 如果数据源连续失败，标记为不可用
            if source.last_error:
                source.is_available = False
                self.logger.warning(f"数据源 {source.name} 暂时不可用")
        
        self.logger.error(f"所有数据源都无法获取数据: {symbol}")
        return None
    
    def get_etf_list(self, market: str = "A") -> Optional[List[Dict[str, Any]]]:
        """获取ETF列表（多数据源故障转移）"""
        # 尝试从缓存获取
        cache_key = f"etf_list_{market}"
        cached_list = self.cache.load(cache_key)
        
        if cached_list is not None:
            cache_age = time.time() - cached_list.get('timestamp', 0)
            if cache_age < 3600:  # 1小时缓存
                self.logger.info(f"从缓存获取ETF列表: {market}")
                return cached_list.get('data', [])
        
        # 尝试从各个数据源获取列表
        for source in self.data_sources:
            if not source.is_available:
                continue
            
            self.logger.info(f"尝试从 {source.name} 获取ETF列表: {market}")
            
            for attempt in range(self.max_retries):
                try:
                    etf_list = source.get_etf_list(market)
                    
                    if etf_list and len(etf_list) > 0:
                        # 缓存列表
                        cache_data = {
                            'data': etf_list,
                            'timestamp': time.time()
                        }
                        self.cache.save(cache_key, cache_data)
                        
                        self.logger.info(f"成功从 {source.name} 获取 {len(etf_list)} 个ETF")
                        return etf_list
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        
                except Exception as e:
                    self.logger.warning(f"{source.name} 获取ETF列表失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    source.last_error = str(e)
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
        
        self.logger.error("所有数据源都无法获取ETF列表")
        return None
    
    def test_all_sources(self) -> Dict[str, Any]:
        """测试所有数据源的连接状态"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'sources': {},
            'available_count': 0,
            'total_count': len(self.data_sources)
        }
        
        for source in self.data_sources:
            try:
                is_connected = source.test_connection()
                source.is_available = is_connected
                
                results['sources'][source.name] = {
                    'available': is_connected,
                    'last_error': source.last_error,
                    'config': bool(source.config)
                }
                
                if is_connected:
                    results['available_count'] += 1
                    
            except Exception as e:
                source.is_available = False
                source.last_error = str(e)
                results['sources'][source.name] = {
                    'available': False,
                    'last_error': str(e),
                    'config': bool(source.config)
                }
        
        return results
    
    def get_source_status(self) -> Dict[str, Any]:
        """获取数据源状态信息"""
        status = {
            'sources': [],
            'primary_source': None,
            'fallback_available': False
        }
        
        for i, source in enumerate(self.data_sources):
            source_info = {
                'name': source.name,
                'available': source.is_available,
                'last_error': source.last_error,
                'is_primary': i == 0
            }
            
            status['sources'].append(source_info)
            
            if i == 0 and source.is_available:
                status['primary_source'] = source.name
            elif source.is_available:
                status['fallback_available'] = True
        
        return status
    
    def _is_cache_valid(self, cached_data: PriceData, start_date: str, end_date: str) -> bool:
        """检查缓存数据是否有效"""
        try:
            if cached_data is None or cached_data.empty:
                return False
            
            # 检查日期范围
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            data_start = cached_data.index.min()
            data_end = cached_data.index.max()
            
            # 缓存数据应该覆盖请求的日期范围
            return data_start <= start_dt and data_end >= end_dt
            
        except Exception:
            return False