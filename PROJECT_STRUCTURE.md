# ETF投资仪表盘 - 项目结构说明

## 📁 项目目录结构

```
etf-dashboard/
├── 📱 etf_dashboard/                    # 主应用包
│   ├── 🎨 app/                         # Streamlit用户界面
│   │   └── dashboard.py                # 主仪表盘应用
│   ├── ⚙️ core/                        # 核心系统组件
│   │   ├── integration.py              # 系统集成器
│   │   ├── error_handler.py            # 错误处理系统
│   │   ├── performance_monitor.py      # 性能监控系统
│   │   ├── ui_error_handler.py         # UI错误处理
│   │   └── data_flow.py                # 数据流管理
│   ├── 📊 data/                        # 数据访问层
│   │   ├── loader.py                   # 数据加载器
│   │   ├── multi_source_loader.py      # 多数据源管理
│   │   ├── cache.py                    # 缓存管理系统
│   │   └── validator.py                # 数据验证器
│   ├── 📈 indicators/                  # 技术指标模块
│   │   └── calculator.py               # 技术指标计算器
│   ├── 🎯 signals/                     # 投资信号模块
│   │   └── manager.py                  # 信号管理器
│   ├── 💼 portfolio/                   # 投资组合模块
│   │   └── manager.py                  # 组合管理器
│   ├── models.py                       # 数据模型定义
│   ├── config.py                       # 配置管理
│   ├── main.py                         # 应用主入口
│   └── __init__.py                     # 包初始化
├── 🔧 config/                          # 配置文件目录
│   └── settings.json                   # 主配置文件
├── 🧪 tests/                           # 测试套件
│   ├── test_basic_structure.py         # 基础结构测试
│   ├── test_data_loader.py             # 数据加载测试
│   ├── test_data_validator.py          # 数据验证测试
│   ├── test_portfolio_manager.py       # 组合管理测试
│   ├── test_signal_manager.py          # 信号管理测试
│   ├── test_system_integration.py      # 系统集成测试
│   ├── test_technical_indicators.py    # 技术指标测试
│   └── __init__.py                     # 测试包初始化
├── 📝 logs/                            # 日志文件目录
│   ├── etf_dashboard.log               # 主日志文件
│   ├── etf_dashboard_errors.log        # 错误日志
│   └── etf_dashboard_performance.log   # 性能日志
├── 💾 data/                            # 数据存储目录
│   └── cache/                          # 缓存数据目录
├── 🐳 .github/                         # GitHub配置
│   └── workflows/                      # CI/CD工作流
│       └── ci.yml                      # 持续集成配置
├── 📋 requirements.txt                 # Python依赖列表
├── 🚀 start_app.py                     # 应用启动脚本
├── 🛑 stop_app.py                      # 应用停止脚本
├── 🎛️ manage_app.py                    # 应用管理脚本
├── 🐳 Dockerfile                       # Docker镜像配置
├── 🐳 docker-compose.yml               # Docker编排配置
├── 📖 README.md                        # 项目说明文档
├── 📄 LICENSE                          # 开源许可证
├── 📊 CHANGELOG.md                     # 版本更新日志
├── 🤝 CONTRIBUTING.md                  # 贡献指南
├── 🎉 RELEASE_NOTES.md                 # 发布说明
├── 🔧 setup.py                         # 包安装配置
├── 🔧 pyproject.toml                   # 项目配置
├── 🔒 .env.example                     # 环境变量示例
├── 🚫 .gitignore                       # Git忽略文件
└── 🚫 .dockerignore                    # Docker忽略文件
```

## 🏗️ 架构设计

### 分层架构
```
┌─────────────────────────────────────┐
│           用户界面层 (UI)            │
│         Streamlit Dashboard         │
├─────────────────────────────────────┤
│          业务逻辑层 (BLL)           │
│    Signals │ Portfolio │ Indicators │
├─────────────────────────────────────┤
│          数据访问层 (DAL)           │
│   Multi-Source Loader │ Cache │ DB  │
├─────────────────────────────────────┤
│           基础设施层 (IL)           │
│  Error Handler │ Monitor │ Config   │
└─────────────────────────────────────┘
```

### 核心组件

#### 🎨 用户界面层
- **dashboard.py**: 主仪表盘，提供完整的Web界面
- **多页面导航**: 概览、ETF详情、组合管理、设置
- **交互式图表**: 基于Plotly的专业金融图表
- **实时更新**: 自动数据刷新和状态同步

#### 🎯 业务逻辑层
- **signals/**: 投资信号生成和管理
- **portfolio/**: 投资组合优化和管理
- **indicators/**: 技术指标计算和分析

#### 📊 数据访问层
- **multi_source_loader.py**: 多数据源管理和故障转移
- **cache.py**: 智能缓存系统
- **validator.py**: 数据质量验证

#### ⚙️ 基础设施层
- **integration.py**: 系统集成和组件协调
- **error_handler.py**: 统一错误处理
- **performance_monitor.py**: 性能监控和优化

## 🔧 配置管理

### 配置文件层次
```
配置优先级 (高到低):
1. 环境变量 (.env)
2. 命令行参数
3. 配置文件 (config/settings.json)
4. 默认值 (代码中定义)
```

### 主要配置项
- **数据源配置**: API密钥、超时、重试次数
- **技术指标参数**: MA周期、RSI参数、阈值
- **投资信号规则**: 过滤条件、置信度阈值
- **系统设置**: 日志级别、缓存策略、UI配置

## 🧪 测试策略

### 测试分类
```
tests/
├── 单元测试 (Unit Tests)
│   ├── test_technical_indicators.py
│   ├── test_data_validator.py
│   └── test_portfolio_manager.py
├── 集成测试 (Integration Tests)
│   ├── test_system_integration.py
│   └── test_data_loader.py
└── 端到端测试 (E2E Tests)
    └── test_basic_structure.py
```

### 测试覆盖
- **单元测试**: 核心算法和业务逻辑
- **集成测试**: 组件间交互和数据流
- **性能测试**: 响应时间和资源使用
- **安全测试**: 输入验证和权限控制

## 🚀 部署方案

### 本地开发
```bash
python start_app.py
```

### Docker部署
```bash
docker-compose up -d
```

### 云端部署
- **Streamlit Cloud**: 一键部署
- **Heroku**: 容器化部署
- **AWS/阿里云**: 自定义部署

## 📊 数据流

### 数据获取流程
```
用户请求 → 缓存检查 → 数据源选择 → API调用 → 数据验证 → 缓存存储 → 返回结果
```

### 信号生成流程
```
价格数据 → 技术指标计算 → 多因子分析 → 信号过滤 → 强度评估 → 信号输出
```

### 组合管理流程
```
ETF数据 → 权重计算 → 风险评估 → 再平衡建议 → 表现分析 → 报告生成
```

## 🔒 安全考虑

### 数据安全
- API密钥通过环境变量管理
- 敏感数据加密存储
- 输入数据严格验证

### 系统安全
- 默认只监听localhost
- 错误信息不暴露系统细节
- 定期安全依赖更新

## 📈 性能优化

### 缓存策略
- **L1缓存**: 内存缓存，毫秒级访问
- **L2缓存**: 磁盘缓存，24小时有效期
- **智能失效**: 基于数据更新时间自动失效

### 数据优化
- **批量获取**: 减少API调用次数
- **增量更新**: 只获取新增数据
- **压缩存储**: 减少存储空间占用

## 🔄 扩展性

### 水平扩展
- 支持多数据源插件
- 可扩展技术指标库
- 模块化投资策略

### 垂直扩展
- 支持更多市场数据
- 增强分析算法
- 扩展用户界面功能

---

这个项目结构设计遵循了软件工程的最佳实践，具有良好的可维护性、可扩展性和可测试性。