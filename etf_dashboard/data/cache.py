"""
数据缓存管理模块

负责ETF数据的本地缓存存储和管理，使用pickle格式存储DataFrame数据。
实现缓存过期检查和自动清理功能。
"""

import os
import pickle
import logging
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from ..models import PriceData


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存配置
        self.cache_expiry_hours = 24  # 缓存有效期24小时
    
    def save(self, symbol: str, data: PriceData) -> None:
        """
        保存数据到缓存
        
        Args:
            symbol: ETF代码
            data: 价格数据
        """
        try:
            cache_file = self._get_cache_file_path(symbol)
            
            # 添加缓存元数据
            cache_data = {
                'data': data,
                'timestamp': datetime.now(),
                'symbol': symbol
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            self.logger.debug(f"数据已缓存: {symbol} -> {cache_file}")
            
        except Exception as e:
            self.logger.error(f"缓存保存失败 {symbol}: {str(e)}")
            raise
    
    def load(self, symbol: str) -> Optional[PriceData]:
        """
        从缓存加载数据
        
        Args:
            symbol: ETF代码
            
        Returns:
            缓存的价格数据，如果不存在或过期返回None
        """
        try:
            cache_file = self._get_cache_file_path(symbol)
            
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查缓存是否过期
            if self._is_cache_expired(cache_data['timestamp']):
                self.logger.debug(f"缓存已过期: {symbol}")
                self._remove_cache_file(cache_file)
                return None
            
            self.logger.debug(f"从缓存加载数据: {symbol}")
            return cache_data['data']
            
        except Exception as e:
            self.logger.error(f"缓存加载失败 {symbol}: {str(e)}")
            return None
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        清理缓存
        
        Args:
            symbol: 指定ETF代码，如果为None则清理所有缓存
        """
        try:
            if symbol:
                # 清理指定ETF的缓存
                cache_file = self._get_cache_file_path(symbol)
                self._remove_cache_file(cache_file)
                self.logger.info(f"已清理缓存: {symbol}")
            else:
                # 清理所有缓存
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.pkl'):
                        file_path = os.path.join(self.cache_dir, filename)
                        self._remove_cache_file(file_path)
                self.logger.info("已清理所有缓存")
                
        except Exception as e:
            self.logger.error(f"缓存清理失败: {str(e)}")
    
    def clear_expired_cache(self) -> None:
        """清理过期的缓存文件"""
        try:
            cleared_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            cache_data = pickle.load(f)
                        
                        if self._is_cache_expired(cache_data['timestamp']):
                            self._remove_cache_file(file_path)
                            cleared_count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"检查缓存文件失败 {file_path}: {str(e)}")
                        # 删除损坏的缓存文件
                        self._remove_cache_file(file_path)
                        cleared_count += 1
            
            if cleared_count > 0:
                self.logger.info(f"已清理 {cleared_count} 个过期缓存文件")
                
        except Exception as e:
            self.logger.error(f"清理过期缓存失败: {str(e)}")
    
    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存统计信息
        """
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            total_size = 0
            valid_count = 0
            expired_count = 0
            
            for filename in cache_files:
                file_path = os.path.join(self.cache_dir, filename)
                total_size += os.path.getsize(file_path)
                
                try:
                    with open(file_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    if self._is_cache_expired(cache_data['timestamp']):
                        expired_count += 1
                    else:
                        valid_count += 1
                        
                except Exception:
                    expired_count += 1
            
            return {
                'total_files': len(cache_files),
                'valid_files': valid_count,
                'expired_files': expired_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': self.cache_dir
            }
            
        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {str(e)}")
            return {}
    
    def _get_cache_file_path(self, symbol: str) -> str:
        """
        获取缓存文件路径
        
        Args:
            symbol: ETF代码
            
        Returns:
            缓存文件完整路径
        """
        filename = f"{symbol}.pkl"
        return os.path.join(self.cache_dir, filename)
    
    def _is_cache_expired(self, timestamp: datetime) -> bool:
        """
        检查缓存是否过期
        
        Args:
            timestamp: 缓存时间戳
            
        Returns:
            是否过期
        """
        expiry_time = timestamp + timedelta(hours=self.cache_expiry_hours)
        return datetime.now() > expiry_time
    
    def _remove_cache_file(self, file_path: str) -> None:
        """
        删除缓存文件
        
        Args:
            file_path: 文件路径
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"已删除缓存文件: {file_path}")
        except Exception as e:
            self.logger.error(f"删除缓存文件失败 {file_path}: {str(e)}")