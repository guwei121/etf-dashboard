"""
性能监控模块

提供函数执行时间监控、内存使用监控、系统资源监控等功能。
支持性能日志记录和性能统计分析。
"""

import time
import functools
import logging
import psutil
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: datetime
    parameters: Dict[str, Any] = None
    result_size: int = 0
    error_occurred: bool = False


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history_size: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_history_size: 最大历史记录数量
        """
        self.logger = logging.getLogger('performance')
        self.max_history_size = max_history_size
        
        # 性能数据存储
        self.metrics_history = deque(maxlen=max_history_size)
        self.function_stats = defaultdict(list)
        self.slow_functions = deque(maxlen=100)  # 慢函数记录
        
        # 配置
        self.slow_threshold = 1.0  # 慢函数阈值（秒）
        self.memory_threshold = 100 * 1024 * 1024  # 内存使用阈值（100MB）
        
        # 系统监控
        self.system_monitor_enabled = False
        self.system_monitor_thread = None
        self.system_metrics = deque(maxlen=100)
        
        # 锁
        self._lock = threading.Lock()
    
    def start_system_monitoring(self, interval: float = 60.0):
        """
        启动系统监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.system_monitor_enabled:
            return
        
        self.system_monitor_enabled = True
        self.system_monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.system_monitor_thread.start()
        self.logger.info(f"系统监控已启动，间隔: {interval}秒")
    
    def stop_system_monitoring(self):
        """停止系统监控"""
        self.system_monitor_enabled = False
        if self.system_monitor_thread:
            self.system_monitor_thread.join(timeout=5.0)
        self.logger.info("系统监控已停止")
    
    def _system_monitor_loop(self, interval: float):
        """系统监控循环"""
        while self.system_monitor_enabled:
            try:
                # 获取系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_metric = {
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'disk_percent': disk.percent,
                    'disk_free': disk.free
                }
                
                with self._lock:
                    self.system_metrics.append(system_metric)
                
                # 记录异常情况
                if cpu_percent > 80:
                    self.logger.warning(f"CPU使用率过高: {cpu_percent:.1f}%")
                
                if memory.percent > 80:
                    self.logger.warning(f"内存使用率过高: {memory.percent:.1f}%")
                
                if disk.percent > 90:
                    self.logger.warning(f"磁盘使用率过高: {disk.percent:.1f}%")
                
                time.sleep(interval)
                
            except Exception as e:
                error_msg = str(e) if e else "未知错误"
                self.logger.error(f"系统监控错误: {error_msg}")
                time.sleep(interval)
    
    def record_metric(self, metric: PerformanceMetric):
        """记录性能指标"""
        with self._lock:
            self.metrics_history.append(metric)
            self.function_stats[metric.function_name].append(metric)
            
            # 检查是否为慢函数
            if metric.execution_time > self.slow_threshold:
                self.slow_functions.append(metric)
                self.logger.warning(
                    f"慢函数检测: {metric.function_name} 执行时间 {metric.execution_time:.3f}s"
                )
            
            # 检查内存使用
            if metric.memory_usage > self.memory_threshold:
                self.logger.warning(
                    f"高内存使用: {metric.function_name} 使用内存 {metric.memory_usage / 1024 / 1024:.1f}MB"
                )
            
            # 记录性能日志
            self.logger.info(
                f"PERF: {metric.function_name} - "
                f"时间: {metric.execution_time:.3f}s, "
                f"内存: {metric.memory_usage / 1024 / 1024:.1f}MB, "
                f"CPU: {metric.cpu_usage:.1f}%"
            )
    
    def get_function_statistics(self, function_name: str = None) -> Dict[str, Any]:
        """
        获取函数统计信息
        
        Args:
            function_name: 函数名称，如果为None则返回所有函数的统计
            
        Returns:
            统计信息字典
        """
        with self._lock:
            if function_name:
                metrics = self.function_stats.get(function_name, [])
                if not metrics:
                    return {}
                
                execution_times = [m.execution_time for m in metrics]
                memory_usages = [m.memory_usage for m in metrics]
                
                return {
                    'function_name': function_name,
                    'call_count': len(metrics),
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'max_execution_time': max(execution_times),
                    'min_execution_time': min(execution_times),
                    'avg_memory_usage': sum(memory_usages) / len(memory_usages),
                    'max_memory_usage': max(memory_usages),
                    'error_count': sum(1 for m in metrics if m.error_occurred),
                    'last_called': max(m.timestamp for m in metrics)
                }
            else:
                # 返回所有函数的统计
                all_stats = {}
                for func_name in self.function_stats:
                    all_stats[func_name] = self.get_function_statistics(func_name)
                return all_stats
    
    def get_slow_functions(self, limit: int = 10) -> List[PerformanceMetric]:
        """
        获取最慢的函数调用
        
        Args:
            limit: 返回数量限制
            
        Returns:
            慢函数列表
        """
        with self._lock:
            sorted_slow = sorted(
                self.slow_functions,
                key=lambda x: x.execution_time,
                reverse=True
            )
            return list(sorted_slow)[:limit]
    
    def get_system_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        获取系统指标
        
        Args:
            minutes: 获取最近多少分钟的数据
            
        Returns:
            系统指标列表
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            return [
                metric for metric in self.system_metrics
                if metric['timestamp'] > cutoff_time
            ]
    
    def clear_metrics(self):
        """清空性能指标"""
        with self._lock:
            self.metrics_history.clear()
            self.function_stats.clear()
            self.slow_functions.clear()
            self.system_metrics.clear()
        
        self.logger.info("性能指标已清空")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        with self._lock:
            total_calls = len(self.metrics_history)
            if total_calls == 0:
                return {'message': '暂无性能数据'}
            
            # 总体统计
            all_times = [m.execution_time for m in self.metrics_history]
            all_memory = [m.memory_usage for m in self.metrics_history]
            
            # 函数统计
            function_stats = {}
            for func_name in self.function_stats:
                function_stats[func_name] = self.get_function_statistics(func_name)
            
            # 最慢函数
            slow_functions = self.get_slow_functions(5)
            
            # 系统指标
            recent_system_metrics = self.get_system_metrics(60)
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'total_function_calls': total_calls,
                'avg_execution_time': sum(all_times) / len(all_times),
                'max_execution_time': max(all_times),
                'avg_memory_usage': sum(all_memory) / len(all_memory),
                'max_memory_usage': max(all_memory),
                'function_statistics': function_stats,
                'slow_functions': [
                    {
                        'function_name': sf.function_name,
                        'execution_time': sf.execution_time,
                        'timestamp': sf.timestamp.isoformat()
                    }
                    for sf in slow_functions
                ],
                'system_metrics_count': len(recent_system_metrics)
            }
            
            return report


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


def monitor_performance(
    include_memory: bool = True,
    include_cpu: bool = True,
    log_slow_calls: bool = True,
    slow_threshold: float = None
):
    """
    性能监控装饰器
    
    Args:
        include_memory: 是否包含内存监控
        include_cpu: 是否包含CPU监控
        log_slow_calls: 是否记录慢调用
        slow_threshold: 慢调用阈值（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 记录开始时间和资源使用
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss if include_memory else 0
            start_cpu = psutil.cpu_percent() if include_cpu else 0
            
            error_occurred = False
            result = None
            result_size = 0
            
            try:
                result = func(*args, **kwargs)
                
                # 计算结果大小
                if result is not None:
                    try:
                        import sys
                        result_size = sys.getsizeof(result)
                    except:
                        result_size = 0
                
                return result
                
            except Exception as e:
                error_occurred = True
                raise
                
            finally:
                # 计算执行时间和资源使用
                execution_time = time.time() - start_time
                end_memory = psutil.Process().memory_info().rss if include_memory else 0
                end_cpu = psutil.cpu_percent() if include_cpu else 0
                
                memory_usage = end_memory - start_memory if include_memory else 0
                cpu_usage = end_cpu - start_cpu if include_cpu else 0
                
                # 创建性能指标
                metric = PerformanceMetric(
                    function_name=f"{func.__module__}.{func.__name__}",
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    timestamp=datetime.now(),
                    parameters={
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    },
                    result_size=result_size,
                    error_occurred=error_occurred
                )
                
                # 记录指标
                performance_monitor.record_metric(metric)
                
                # 检查慢调用
                threshold = slow_threshold or performance_monitor.slow_threshold
                if log_slow_calls and execution_time > threshold:
                    logging.getLogger().warning(
                        f"慢函数调用: {func.__name__} 执行时间 {execution_time:.3f}s"
                    )
        
        return wrapper
    return decorator


def start_performance_monitoring(interval: float = 60.0):
    """启动性能监控"""
    performance_monitor.start_system_monitoring(interval)


def stop_performance_monitoring():
    """停止性能监控"""
    performance_monitor.stop_system_monitoring()


def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    return performance_monitor.generate_performance_report()


def clear_performance_data():
    """清空性能数据"""
    performance_monitor.clear_metrics()