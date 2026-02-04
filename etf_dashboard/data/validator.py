"""
数据验证和格式化模块

负责验证从外部数据源获取的数据质量，进行数据类型转换和格式标准化。
处理缺失值、异常值和数据完整性检查。
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any
import numpy as np
from datetime import datetime

from ..models import PriceData


class DataValidator:
    """数据验证和格式化器"""
    
    def __init__(self):
        """初始化数据验证器"""
        self.logger = logging.getLogger(__name__)
        
        # 标准列名映射 (akshare -> 标准格式)
        self.column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close', 
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover'
        }
        
        # 必需的列
        self.required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    
    def validate_price_data(self, data: pd.DataFrame, enable_outlier_detection: bool = False, 
                           price_precision: int = 2) -> Optional[PriceData]:
        """
        验证和格式化价格数据
        
        Args:
            data: 原始价格数据DataFrame
            enable_outlier_detection: 是否启用异常值检测
            price_precision: 价格精度（小数位数）
            
        Returns:
            验证和格式化后的价格数据，验证失败返回None
        """
        try:
            if data is None or data.empty:
                self.logger.warning("输入数据为空")
                return None
            
            # 1. 标准化列名
            standardized_data = self._standardize_columns(data)
            if standardized_data is None:
                return None
            
            # 2. 验证必需列
            if not self._validate_required_columns(standardized_data):
                return None
            
            # 3. 数据类型转换
            converted_data = self._convert_data_types(standardized_data)
            if converted_data is None:
                return None
            
            # 4. 处理缺失值
            cleaned_data = self._handle_missing_values(converted_data)
            if cleaned_data is None:
                return None
            
            # 5. 数据完整性检查
            if not self._validate_data_integrity(cleaned_data):
                return None
            
            # 6. 设置日期索引
            final_data = self._set_date_index(cleaned_data)
            if final_data is None:
                return None
            
            # 7. 排序数据
            final_data = final_data.sort_index()
            
            # 8. 格式化价格精度
            final_data = self.format_price_precision(final_data, price_precision)
            
            # 9. 统一日期时间格式
            final_data = self.normalize_datetime_format(final_data)
            
            # 10. 可选的异常值检测
            if enable_outlier_detection:
                final_data = self.detect_outliers(final_data)
            
            # 11. 最终数据完整性验证
            if not self.validate_data_completeness(final_data):
                self.logger.warning("数据完整性验证未通过，但仍返回数据")
            
            self.logger.debug(f"数据验证成功，共 {len(final_data)} 条记录")
            return final_data
            
        except Exception as e:
            self.logger.error(f"数据验证失败: {str(e)}")
            return None
    
    def validate_etf_code(self, code: str) -> bool:
        """
        验证ETF代码格式
        
        Args:
            code: ETF代码
            
        Returns:
            是否为有效格式
        """
        if not code or not isinstance(code, str):
            return False
        
        code = code.strip()
        
        # A股ETF: 6位数字
        if len(code) == 6 and code.isdigit():
            return True
        
        # 美股ETF: 2-5位字母
        if 2 <= len(code) <= 5 and code.isalpha():
            return True
        
        return False
    
    def format_price_precision(self, data: pd.DataFrame, price_precision: int = 2, volume_precision: int = 0) -> pd.DataFrame:
        """
        格式化价格和成交量的精度
        
        Args:
            data: 价格数据
            price_precision: 价格小数位数
            volume_precision: 成交量小数位数
            
        Returns:
            格式化后的数据
        """
        try:
            result = data.copy()
            
            # 格式化价格列
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in result.columns:
                    result[col] = result[col].round(price_precision)
            
            # 格式化成交量
            if 'volume' in result.columns:
                result['volume'] = result['volume'].round(volume_precision).astype('int64')
            
            self.logger.debug(f"价格精度格式化完成: 价格{price_precision}位小数，成交量{volume_precision}位小数")
            return result
            
        except Exception as e:
            self.logger.error(f"价格精度格式化失败: {str(e)}")
            return data
    
    def detect_outliers(self, data: pd.DataFrame, method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:
        """
        检测和标记异常值
        
        Args:
            data: 价格数据
            method: 异常值检测方法 ('iqr', 'zscore')
            threshold: 异常值阈值
            
        Returns:
            包含异常值标记的数据
        """
        try:
            result = data.copy()
            result['is_outlier'] = False
            
            # 检测价格异常值
            price_columns = ['open', 'high', 'low', 'close']
            
            for col in price_columns:
                if col in result.columns:
                    if method == 'iqr':
                        # 使用四分位距方法
                        Q1 = result[col].quantile(0.25)
                        Q3 = result[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - threshold * IQR
                        upper_bound = Q3 + threshold * IQR
                        
                        outliers = (result[col] < lower_bound) | (result[col] > upper_bound)
                        result.loc[outliers, 'is_outlier'] = True
                        
                    elif method == 'zscore':
                        # 使用Z分数方法
                        z_scores = np.abs((result[col] - result[col].mean()) / result[col].std())
                        outliers = z_scores > threshold
                        result.loc[outliers, 'is_outlier'] = True
            
            outlier_count = result['is_outlier'].sum()
            if outlier_count > 0:
                self.logger.warning(f"检测到 {outlier_count} 个异常值")
            
            return result
            
        except Exception as e:
            self.logger.error(f"异常值检测失败: {str(e)}")
            return data
    
    def normalize_datetime_format(self, data: pd.DataFrame, datetime_format: str = None) -> pd.DataFrame:
        """
        统一日期时间格式
        
        Args:
            data: 包含日期时间的数据
            datetime_format: 目标日期时间格式
            
        Returns:
            格式化后的数据
        """
        try:
            result = data.copy()
            
            # 处理索引中的日期时间
            if isinstance(result.index, pd.DatetimeIndex):
                if datetime_format:
                    # 如果指定了格式，转换为字符串再转回datetime
                    result.index = pd.to_datetime(result.index.strftime(datetime_format))
                else:
                    # 标准化为pandas datetime格式
                    result.index = pd.to_datetime(result.index)
                    
            # 处理列中的日期时间
            for col in result.columns:
                if result[col].dtype == 'object':
                    # 尝试转换为datetime
                    try:
                        result[col] = pd.to_datetime(result[col], errors='ignore')
                    except:
                        pass
            
            self.logger.debug("日期时间格式统一完成")
            return result
            
        except Exception as e:
            self.logger.error(f"日期时间格式统一失败: {str(e)}")
            return data
    
    def validate_data_completeness(self, data: pd.DataFrame, min_records: int = 30) -> bool:
        """
        验证数据完整性和最小记录数
        
        Args:
            data: 数据DataFrame
            min_records: 最小记录数要求
            
        Returns:
            数据是否满足完整性要求
        """
        try:
            if data is None or data.empty:
                self.logger.error("数据为空")
                return False
            
            # 检查最小记录数
            if len(data) < min_records:
                self.logger.error(f"数据记录数不足: {len(data)} < {min_records}")
                return False
            
            # 检查必需列的完整性
            for col in self.required_columns:
                if col not in data.columns:
                    continue
                    
                missing_rate = data[col].isna().sum() / len(data)
                if missing_rate > 0.1:  # 缺失率超过10%
                    self.logger.error(f"列 {col} 缺失率过高: {missing_rate:.2%}")
                    return False
            
            # 检查时间序列连续性
            if isinstance(data.index, pd.DatetimeIndex):
                date_gaps = data.index.to_series().diff().dt.days
                large_gaps = date_gaps[date_gaps > 7]  # 超过7天的间隔
                if len(large_gaps) > len(data) * 0.1:  # 大间隔超过10%
                    self.logger.warning(f"时间序列存在较多大间隔: {len(large_gaps)} 个")
            
            self.logger.debug("数据完整性验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"数据完整性验证失败: {str(e)}")
            return False
    
    def _standardize_columns(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        标准化列名
        
        Args:
            data: 原始数据
            
        Returns:
            标准化后的数据
        """
        try:
            # 创建数据副本
            result = data.copy()
            
            # 重命名列
            result.columns = [self.column_mapping.get(col, col) for col in result.columns]
            
            self.logger.debug(f"列名标准化完成: {list(result.columns)}")
            return result
            
        except Exception as e:
            self.logger.error(f"列名标准化失败: {str(e)}")
            return None
    
    def _validate_required_columns(self, data: pd.DataFrame) -> bool:
        """
        验证必需列是否存在
        
        Args:
            data: 数据DataFrame
            
        Returns:
            是否包含所有必需列
        """
        missing_columns = [col for col in self.required_columns if col not in data.columns]
        
        if missing_columns:
            self.logger.error(f"缺少必需列: {missing_columns}")
            return False
        
        return True
    
    def _convert_data_types(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        转换数据类型
        
        Args:
            data: 原始数据
            
        Returns:
            类型转换后的数据
        """
        try:
            result = data.copy()
            
            # 转换日期列
            if 'date' in result.columns:
                result['date'] = pd.to_datetime(result['date'], errors='coerce')
            
            # 转换数值列
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in result.columns:
                    result[col] = pd.to_numeric(result[col], errors='coerce')
            
            # 转换成交量为整数
            if 'volume' in result.columns:
                result['volume'] = result['volume'].fillna(0).astype('int64')
            
            self.logger.debug("数据类型转换完成")
            return result
            
        except Exception as e:
            self.logger.error(f"数据类型转换失败: {str(e)}")
            return None
    
    def _handle_missing_values(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        处理缺失值
        
        Args:
            data: 原始数据
            
        Returns:
            处理缺失值后的数据
        """
        try:
            result = data.copy()
            
            # 检查关键列的缺失值
            critical_columns = ['date', 'open', 'high', 'low', 'close']
            for col in critical_columns:
                if col in result.columns:
                    missing_count = result[col].isna().sum()
                    if missing_count > 0:
                        self.logger.warning(f"列 {col} 有 {missing_count} 个缺失值")
                        
                        if col == 'date':
                            # 日期缺失则删除该行
                            result = result.dropna(subset=[col])
                        else:
                            # 价格缺失使用前向填充
                            result[col] = result[col].ffill()
            
            # 删除仍有缺失值的行
            result = result.dropna(subset=critical_columns)
            
            if result.empty:
                self.logger.error("处理缺失值后数据为空")
                return None
            
            self.logger.debug(f"缺失值处理完成，剩余 {len(result)} 条记录")
            return result
            
        except Exception as e:
            self.logger.error(f"缺失值处理失败: {str(e)}")
            return None
    
    def _validate_data_integrity(self, data: pd.DataFrame) -> bool:
        """
        验证数据完整性
        
        Args:
            data: 数据DataFrame
            
        Returns:
            数据是否完整有效
        """
        try:
            # 检查价格逻辑
            invalid_price_rows = 0
            for idx, row in data.iterrows():
                # 最高价应该 >= 最低价
                if row['high'] < row['low']:
                    invalid_price_rows += 1
                    continue
                
                # 开盘价和收盘价应该在最高价和最低价之间
                if not (row['low'] <= row['open'] <= row['high']):
                    invalid_price_rows += 1
                    continue
                    
                if not (row['low'] <= row['close'] <= row['high']):
                    invalid_price_rows += 1
                    continue
                
                # 价格应该为正数
                if any(row[col] <= 0 for col in ['open', 'high', 'low', 'close']):
                    invalid_price_rows += 1
                    continue
                
                # 成交量应该为非负数
                if row['volume'] < 0:
                    invalid_price_rows += 1
                    continue
            
            if invalid_price_rows > 0:
                error_rate = invalid_price_rows / len(data)
                if error_rate > 0.1:  # 错误率超过10%
                    self.logger.error(f"数据完整性检查失败，错误率: {error_rate:.2%}")
                    return False
                else:
                    self.logger.warning(f"发现 {invalid_price_rows} 条异常数据，错误率: {error_rate:.2%}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据完整性检查失败: {str(e)}")
            return False
    
    def _set_date_index(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        设置日期索引
        
        Args:
            data: 数据DataFrame
            
        Returns:
            设置索引后的数据
        """
        try:
            result = data.copy()
            
            if 'date' in result.columns:
                result.set_index('date', inplace=True)
                result.index.name = 'date'
            
            self.logger.debug("日期索引设置完成")
            return result
            
        except Exception as e:
            self.logger.error(f"日期索引设置失败: {str(e)}")
            return None