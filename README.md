# ETF投资仪表盘

一个基于Streamlit的专业ETF投资分析仪表盘，提供实时数据获取、技术指标分析、投资信号生成和投资组合管理功能。

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ 功能特性

### 🎯 核心功能
- **多数据源支持**: 集成akshare和tushare数据源，支持自动故障转移
- **技术指标分析**: MA5/20/30、RSI14、最大回撤等专业技术指标
- **智能信号生成**: 基于多重技术分析的买入/卖出信号
- **投资组合管理**: 专业的组合配置、权重管理和再平衡功能
- **实时性能监控**: 系统性能监控和智能错误处理

### � 技术特性
- **模块化架构**: 清晰的组件分离，易于扩展和维护
- **健壮错误处理**: 完善的错误处理和自动恢复机制
- **智能缓存系统**: 多层缓存机制，显著提升响应速度
- **灵活配置管理**: JSON配置文件，支持运行时动态调整
- **详细日志记录**: 分级日志系统，便于问题诊断

## � 快速开始

### 📋 环境要求
- Python 3.8+
- 8GB+ RAM (推荐)
- 稳定的网络连接

### �️ 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/etf-dashboard.git
cd etf-dashboard
```

2. **创建虚拟环境**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境**
```bash
cp .env.example .env
# 编辑 .env 文件，配置API密钥
```

5. **启动应用**
```bash
# 方式1: 使用启动脚本
python start_app.py

# 方式2: 直接使用Streamlit
streamlit run etf_dashboard/main.py

# 方式3: 使用管理脚本
python manage_app.py start
```

访问 http://localhost:8501 查看应用

## ⚙️ 配置说明

### 数据源配置

编辑 `config/settings.json` 配置数据源：

```json
{
  "data": {
    "data_sources": {
      "akshare": {
        "enabled": true,
        "priority": 1,
        "timeout": 30,
        "max_retries": 3
      },
      "tushare": {
        "enabled": true,
        "priority": 2,
        "timeout": 30,
        "max_retries": 3,
        "token": "your_tushare_token",
        "proxy_url": "http://your-proxy-url"
      }
    }
  }
}
```

### 技术指标配置

```json
{
  "indicators": {
    "ma_periods": [5, 20, 30],
    "rsi_period": 14,
    "rsi_overbought": 70.0,
    "rsi_oversold": 30.0
  }
}
```

### 环境变量配置

创建 `.env` 文件：
```env
# Tushare配置
TUSHARE_TOKEN=your_tushare_token_here
TUSHARE_PROXY_URL=http://your-proxy-url

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/etf_dashboard.log

# 缓存配置
CACHE_DIR=data/cache
CACHE_EXPIRY_HOURS=24
```

## � 项目结构

```
etf-dashboard/
├── 📱 etf_dashboard/           # 主应用包
│   ├── 🎨 app/                # Streamlit界面
│   │   └── dashboard.py       # 主仪表盘
│   ├── ⚙️ core/               # 核心组件
│   │   ├── integration.py     # 系统集成器
│   │   ├── error_handler.py   # 错误处理
│   │   ├── performance_monitor.py # 性能监控
│   │   └── ui_error_handler.py # UI错误处理
│   ├── 📊 data/               # 数据层
│   │   ├── loader.py          # 数据加载器
│   │   ├── multi_source_loader.py # 多数据源
│   │   ├── cache.py           # 缓存管理
│   │   └── validator.py       # 数据验证
│   ├── 📈 indicators/         # 技术指标
│   │   └── calculator.py      # 指标计算器
│   ├── 🎯 signals/            # 投资信号
│   │   └── manager.py         # 信号管理器
│   ├── 💼 portfolio/          # 投资组合
│   │   └── manager.py         # 组合管理器
│   ├── models.py              # 数据模型
│   ├── config.py              # 配置管理
│   └── main.py                # 应用入口
├── 🔧 config/                 # 配置文件
│   └── settings.json          # 主配置文件
├── 🧪 tests/                  # 测试套件
├── 📝 logs/                   # 日志文件
├── 💾 data/                   # 数据缓存
├── 📋 requirements.txt        # Python依赖
├── 🚀 start_app.py           # 启动脚本
├── 🛑 stop_app.py            # 停止脚本
├── 🎛️ manage_app.py          # 管理脚本
└── 📖 README.md              # 项目文档
```

## 📖 使用指南

### 1. 📊 数据获取
- **多市场支持**: A股、美股ETF数据
- **智能故障转移**: 主数据源失败时自动切换
- **缓存优化**: 智能缓存减少API调用

### 2. 📈 技术分析
- **移动平均线**: MA5、MA20、MA30多周期分析
- **RSI指标**: 14周期相对强弱指数
- **趋势识别**: 自动识别上升、下降、震荡趋势
- **风险控制**: 最大回撤计算和监控

### 3. 🎯 投资信号
- **多因子模型**: 结合趋势、RSI、回撤等多个因子
- **信号过滤**: 智能过滤假信号
- **强度评估**: 信号强度量化评分

### 4. 💼 投资组合
- **多ETF组合**: 支持多只ETF的组合配置
- **权重管理**: 灵活的权重分配和调整
- **再平衡**: 自动再平衡建议
- **表现分析**: 组合收益和风险分析

## 🔧 开发指南

### 添加新数据源

1. 继承 `DataSourceInterface` 基类：
```python
class NewDataSource(DataSourceInterface):
    def get_etf_data(self, symbol, start_date, end_date):
        # 实现数据获取逻辑
        pass
    
    def get_etf_list(self, market="A"):
        # 实现ETF列表获取
        pass
    
    def test_connection(self):
        # 实现连接测试
        pass
```

2. 在配置文件中添加数据源配置
3. 在 `MultiSourceDataLoader` 中注册新数据源

### 添加新技术指标

1. 在 `TechnicalIndicators` 类中添加计算方法
2. 更新 `TechnicalData` 数据模型
3. 在配置文件中添加指标参数

### 自定义投资策略

1. 在 `SignalManager` 中实现策略逻辑
2. 定义策略参数和过滤条件
3. 集成到信号生成流程

## 🧪 测试

### 运行完整测试套件
```bash
python -m pytest tests/ -v
```

### 运行特定测试
```bash
# 测试技术指标
python -m pytest tests/test_technical_indicators.py -v

# 测试数据加载
python -m pytest tests/test_data_loader.py -v

# 测试信号生成
python -m pytest tests/test_signal_manager.py -v
```

### 测试覆盖率
```bash
python -m pytest tests/ --cov=etf_dashboard --cov-report=html
```

## 🚀 部署

### 本地部署
```bash
# 启动应用
python start_app.py

# 后台运行
nohup python start_app.py > app.log 2>&1 &
```

### Docker部署
```bash
# 构建镜像
docker build -t etf-dashboard .

# 运行容器
docker run -d -p 8501:8501 --name etf-dashboard etf-dashboard

# 使用docker-compose
docker-compose up -d
```

### 云部署
支持部署到：
- Streamlit Cloud
- Heroku
- AWS EC2
- 阿里云ECS

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献流程
1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持与联系

- 🐛 **Bug报告**: [提交Issue](https://github.com/guwei121/etf-dashboard/issues)
- 💡 **功能建议**: [功能请求](https://github.com/guwei121/etf-dashboard/issues)
- 📧 **邮件联系**: cuuve0326@gmail.com
- 💬 **讨论交流**: [Discussions](https://github.com/guwei121/etf-dashboard/discussions)

## 🎉 致谢

感谢以下开源项目：
- [Streamlit](https://streamlit.io/) - 优秀的Web应用框架
- [akshare](https://github.com/akfamily/akshare) - 金融数据接口
- [tushare](https://github.com/waditu/tushare) - 金融数据平台
- [pandas](https://pandas.pydata.org/) - 数据分析库
- [plotly](https://plotly.com/) - 交互式图表库

## 📊 更新日志

### v1.0.0 (2024-02-04)
- ✨ 初始版本发布
- 🎯 多数据源ETF数据获取
- 📈 完整技术指标分析系统
- 🎯 智能投资信号生成
- 💼 专业投资组合管理
- 🔧 健壮的错误处理和监控
- 📱 响应式Web界面
- 🧪 完整测试套件

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！