"""
系统配置管理

负责管理系统的各种配置参数，包括数据源配置、技术指标参数、
信号规则配置和界面设置等。支持从配置文件加载和环境变量覆盖。
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime


@dataclass
class DataConfig:
    """数据相关配置"""
    cache_dir: str = "data/cache"
    cache_expiry_hours: int = 24
    api_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    data_sources: dict = None
    
    def __post_init__(self):
        if self.data_sources is None:
            self.data_sources = {
                "use_multi_source": True,
                "akshare": {
                    "enabled": True,
                    "priority": 1,
                    "timeout": 30,
                    "max_retries": 3
                },
                "tushare": {
                    "enabled": True,
                    "priority": 2,
                    "timeout": 30,
                    "max_retries": 3,
                    "token": "292f5bf5d3067a0d7bdfe9873e4df4b878c4d3ac690ed8743266855b76cf",
                    "proxy_url": "http://lianghua.nanyangqiankun.top"
                }
            }


@dataclass
class IndicatorConfig:
    """技术指标配置"""
    ma_periods: list = None
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_neutral: float = 50.0
    
    def __post_init__(self):
        if self.ma_periods is None:
            self.ma_periods = [5, 20, 60]


@dataclass
class SignalConfig:
    """信号规则配置"""
    max_drawdown_threshold: float = 0.20
    trend_strength_threshold: float = 0.6
    confidence_threshold: float = 0.5
    enable_trend_filter: bool = True
    enable_rsi_filter: bool = True
    enable_drawdown_filter: bool = True


@dataclass
class PortfolioConfig:
    """组合管理配置"""
    default_rebalance_threshold: float = 0.05
    config_file: str = "data/portfolio_config.json"
    auto_save: bool = True
    max_positions: int = 20


@dataclass
class UIConfig:
    """界面配置"""
    page_title: str = "ETF投资仪表盘"
    page_icon: str = "📈"
    layout: str = "wide"
    sidebar_state: str = "expanded"
    theme: str = "light"
    chart_height: int = 400
    show_debug_info: bool = False


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/etf_dashboard.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    # 新增配置项
    enable_structured_logging: bool = True
    log_to_file: bool = True
    error_log_file: str = "logs/etf_dashboard_errors.log"
    performance_log_file: str = "logs/etf_dashboard_performance.log"
    enable_performance_logging: bool = True
    log_rotation_when: str = "midnight"  # 日志轮转时间
    log_rotation_interval: int = 1  # 轮转间隔
    enable_json_logging: bool = False  # JSON格式日志
    sensitive_data_fields: list = None  # 敏感数据字段
    
    def __post_init__(self):
        if self.sensitive_data_fields is None:
            self.sensitive_data_fields = ['password', 'token', 'key', 'secret']


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config/settings.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.data = DataConfig()
        self.indicators = IndicatorConfig()
        self.signals = SignalConfig()
        self.portfolio = PortfolioConfig()
        self.ui = UIConfig()
        self.logging = LogConfig()
        
        # 加载配置
        self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> None:
        """从配置文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新各模块配置
                if 'data' in config_data:
                    self._update_config(self.data, config_data['data'])
                
                if 'indicators' in config_data:
                    self._update_config(self.indicators, config_data['indicators'])
                
                if 'signals' in config_data:
                    self._update_config(self.signals, config_data['signals'])
                
                if 'portfolio' in config_data:
                    self._update_config(self.portfolio, config_data['portfolio'])
                
                if 'ui' in config_data:
                    self._update_config(self.ui, config_data['ui'])
                
                if 'logging' in config_data:
                    self._update_config(self.logging, config_data['logging'])
                
                self.logger.info(f"配置已从文件加载: {self.config_file}")
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                self._create_default_config()
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            self.logger.info("使用默认配置")
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        try:
            # 数据配置环境变量
            if os.getenv('ETF_CACHE_DIR'):
                self.data.cache_dir = os.getenv('ETF_CACHE_DIR')
            
            if os.getenv('ETF_CACHE_EXPIRY_HOURS'):
                self.data.cache_expiry_hours = int(os.getenv('ETF_CACHE_EXPIRY_HOURS'))
            
            # 日志配置环境变量
            if os.getenv('ETF_LOG_LEVEL'):
                self.logging.level = os.getenv('ETF_LOG_LEVEL').upper()
            
            if os.getenv('ETF_LOG_FILE'):
                self.logging.file_path = os.getenv('ETF_LOG_FILE')
            
            # 界面配置环境变量
            if os.getenv('ETF_DEBUG'):
                self.ui.show_debug_info = os.getenv('ETF_DEBUG').lower() == 'true'
            
            self.logger.debug("环境变量覆盖已应用")
            
        except Exception as e:
            self.logger.error(f"应用环境变量覆盖失败: {str(e)}")
    
    def _update_config(self, config_obj: Any, config_dict: Dict[str, Any]) -> None:
        """更新配置对象"""
        for key, value in config_dict.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
    
    def _create_default_config(self) -> None:
        """创建默认配置文件"""
        try:
            # 创建配置目录
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 生成默认配置
            default_config = {
                'data': asdict(self.data),
                'indicators': asdict(self.indicators),
                'signals': asdict(self.signals),
                'portfolio': asdict(self.portfolio),
                'ui': asdict(self.ui),
                'logging': asdict(self.logging)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"默认配置文件已创建: {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"创建默认配置文件失败: {str(e)}")
    
    def save_config(self) -> None:
        """保存当前配置到文件"""
        try:
            config_data = {
                'data': asdict(self.data),
                'indicators': asdict(self.indicators),
                'signals': asdict(self.signals),
                'portfolio': asdict(self.portfolio),
                'ui': asdict(self.ui),
                'logging': asdict(self.logging)
            }
            
            # 创建配置目录
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("配置已保存到文件")
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            raise
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return {
            'data': asdict(self.data),
            'indicators': asdict(self.indicators),
            'signals': asdict(self.signals),
            'portfolio': asdict(self.portfolio),
            'ui': asdict(self.ui),
            'logging': asdict(self.logging)
        }
    
    def update_config(self, section: str, updates: Dict[str, Any]) -> None:
        """
        更新指定配置节
        
        Args:
            section: 配置节名称 ('data', 'indicators', 'signals', 'portfolio', 'ui', 'logging')
            updates: 更新的配置项
        """
        try:
            config_obj = getattr(self, section)
            self._update_config(config_obj, updates)
            self.logger.info(f"配置节 {section} 已更新")
            
        except AttributeError:
            raise ValueError(f"无效的配置节: {section}")
        except Exception as e:
            self.logger.error(f"更新配置节失败 {section}: {str(e)}")
            raise


# 全局配置实例
config = ConfigManager()


def get_config() -> ConfigManager:
    """获取全局配置实例"""
    return config


def setup_logging(config_manager: Optional[ConfigManager] = None) -> None:
    """
    设置日志系统
    
    Args:
        config_manager: 配置管理器实例，如果为None则使用全局配置
    """
    if config_manager is None:
        config_manager = config
    
    log_config = config_manager.logging
    
    try:
        # 创建日志目录
        log_dir = os.path.dirname(log_config.file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建错误日志目录
        if log_config.log_to_file and log_config.error_log_file:
            error_log_dir = os.path.dirname(log_config.error_log_file)
            if error_log_dir:
                os.makedirs(error_log_dir, exist_ok=True)
        
        # 创建性能日志目录
        if log_config.enable_performance_logging and log_config.performance_log_file:
            perf_log_dir = os.path.dirname(log_config.performance_log_file)
            if perf_log_dir:
                os.makedirs(perf_log_dir, exist_ok=True)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_config.level))
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建格式器
        if log_config.enable_json_logging:
            formatter = JsonFormatter()
        else:
            formatter = SensitiveDataFormatter(
                log_config.format,
                sensitive_fields=log_config.sensitive_data_fields
            )
        
        # 主日志文件处理器
        if log_config.log_to_file:
            from logging.handlers import TimedRotatingFileHandler
            
            file_handler = TimedRotatingFileHandler(
                log_config.file_path,
                when=log_config.log_rotation_when,
                interval=log_config.log_rotation_interval,
                backupCount=log_config.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # 错误日志文件处理器
        if log_config.log_to_file and log_config.error_log_file:
            from logging.handlers import RotatingFileHandler
            
            error_handler = RotatingFileHandler(
                log_config.error_log_file,
                maxBytes=log_config.max_file_size,
                backupCount=log_config.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
        
        # 性能日志处理器
        if log_config.enable_performance_logging and log_config.performance_log_file:
            perf_logger = logging.getLogger('performance')
            perf_handler = logging.FileHandler(log_config.performance_log_file, encoding='utf-8')
            perf_handler.setFormatter(formatter)
            perf_logger.addHandler(perf_handler)
            perf_logger.setLevel(logging.INFO)
            perf_logger.propagate = False  # 不传播到根日志器
        
        # 控制台处理器
        if log_config.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            
            # 控制台只显示WARNING及以上级别
            console_handler.setLevel(logging.WARNING)
            root_logger.addHandler(console_handler)
        
        # 设置第三方库的日志级别
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('matplotlib').setLevel(logging.WARNING)
        logging.getLogger('plotly').setLevel(logging.WARNING)
        
        logging.info("增强日志系统初始化完成")
        logging.info(f"日志级别: {log_config.level}")
        logging.info(f"主日志文件: {log_config.file_path}")
        if log_config.error_log_file:
            logging.info(f"错误日志文件: {log_config.error_log_file}")
        if log_config.enable_performance_logging:
            logging.info(f"性能日志文件: {log_config.performance_log_file}")
        
    except Exception as e:
        print(f"日志系统初始化失败: {str(e)}")
        # 使用基本配置作为后备
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


class SensitiveDataFormatter(logging.Formatter):
    """敏感数据过滤格式器"""
    
    def __init__(self, fmt=None, datefmt=None, sensitive_fields=None):
        super().__init__(fmt, datefmt)
        self.sensitive_fields = sensitive_fields or []
    
    def format(self, record):
        # 过滤敏感数据
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for field in self.sensitive_fields:
                if field.lower() in record.msg.lower():
                    record.msg = record.msg.replace(field, '*' * len(field))
        
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式器"""
    
    def format(self, record):
        import json
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


def get_performance_logger():
    """获取性能日志器"""
    return logging.getLogger('performance')


def log_performance(func_name: str, duration: float, **kwargs):
    """记录性能日志"""
    perf_logger = get_performance_logger()
    extra_info = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    perf_logger.info(f"PERF: {func_name} took {duration:.3f}s {extra_info}")


def create_structured_log_entry(
    level: str,
    message: str,
    category: str = None,
    component: str = None,
    **extra_fields
) -> Dict[str, Any]:
    """
    创建结构化日志条目
    
    Args:
        level: 日志级别
        message: 日志消息
        category: 日志类别
        component: 组件名称
        **extra_fields: 额外字段
        
    Returns:
        结构化日志字典
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level.upper(),
        'message': message
    }
    
    if category:
        log_entry['category'] = category
    
    if component:
        log_entry['component'] = component
    
    log_entry.update(extra_fields)
    
    return log_entry