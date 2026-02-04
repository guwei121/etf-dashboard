# 贡献指南

感谢您对ETF投资仪表盘项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 Bug报告
- 💡 功能建议
- 📝 文档改进
- 🔧 代码贡献
- 🧪 测试用例
- 🌐 翻译工作

## 🚀 快速开始

### 开发环境设置

1. **Fork项目**
   ```bash
   # 在GitHub上Fork项目，然后克隆到本地
   git clone https://github.com/your-username/etf-dashboard.git
   cd etf-dashboard
   ```

2. **设置开发环境**
   ```bash
   # 创建虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   
   # 安装依赖
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # 开发依赖
   ```

3. **配置开发环境**
   ```bash
   # 复制环境配置
   cp .env.example .env
   
   # 编辑配置文件
   # 配置测试用的API密钥等
   ```

4. **运行测试**
   ```bash
   # 运行完整测试套件
   python -m pytest tests/ -v
   
   # 运行代码质量检查
   flake8 etf_dashboard/
   black --check etf_dashboard/
   ```

## 📋 贡献流程

### 1. 创建Issue

在开始编码之前，请先创建一个Issue来描述：
- 🐛 **Bug报告**：详细描述问题、复现步骤、期望行为
- 💡 **功能请求**：说明功能需求、使用场景、实现建议
- 📝 **文档改进**：指出文档问题或改进建议

### 2. 分支管理

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 或创建修复分支
git checkout -b fix/issue-number-description

# 或创建文档分支
git checkout -b docs/documentation-improvement
```

### 3. 开发规范

#### 代码风格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 代码风格
- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 使用 [flake8](https://flake8.pycqa.org/) 进行代码检查

```bash
# 格式化代码
black etf_dashboard/

# 检查代码风格
flake8 etf_dashboard/
```

#### 文档字符串
使用Google风格的文档字符串：

```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    计算相对强弱指数(RSI)
    
    Args:
        prices: 价格序列
        period: 计算周期，默认14
        
    Returns:
        RSI值序列
        
    Raises:
        ValueError: 当价格序列为空或周期无效时
        
    Example:
        >>> prices = pd.Series([100, 101, 99, 102])
        >>> rsi = calculate_rsi(prices, period=14)
    """
```

#### 类型注解
使用类型注解提高代码可读性：

```python
from typing import List, Dict, Optional, Union
import pandas as pd

def get_etf_data(
    symbol: str, 
    start_date: str, 
    end_date: str
) -> Optional[pd.DataFrame]:
    """获取ETF数据"""
    pass
```

### 4. 测试要求

#### 单元测试
- 为新功能编写单元测试
- 确保测试覆盖率不低于80%
- 使用pytest框架

```python
import pytest
import pandas as pd
from etf_dashboard.indicators.calculator import TechnicalIndicators

class TestTechnicalIndicators:
    def setup_method(self):
        self.calculator = TechnicalIndicators()
        
    def test_calculate_rsi(self):
        """测试RSI计算"""
        prices = pd.Series([100, 101, 99, 102, 98])
        rsi = self.calculator.calculate_rsi(prices, period=4)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(prices)
```

#### 集成测试
- 测试组件间的交互
- 验证数据流的完整性
- 测试错误处理机制

### 5. 提交规范

#### 提交信息格式
使用约定式提交格式：

```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

**类型说明：**
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例：**
```bash
git commit -m "feat(indicators): 添加MACD技术指标计算"
git commit -m "fix(data): 修复tushare数据源连接超时问题"
git commit -m "docs(readme): 更新安装说明"
```

### 6. Pull Request

#### PR标题和描述
- 标题简洁明了，说明主要变更
- 描述中包含：
  - 变更内容概述
  - 相关Issue链接
  - 测试说明
  - 截图（如适用）

#### PR检查清单
- [ ] 代码遵循项目风格规范
- [ ] 添加了适当的测试
- [ ] 测试全部通过
- [ ] 文档已更新
- [ ] 变更日志已更新
- [ ] 没有引入破坏性变更

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_technical_indicators.py -v

# 运行特定测试方法
python -m pytest tests/test_technical_indicators.py::TestTechnicalIndicators::test_calculate_rsi -v

# 生成覆盖率报告
python -m pytest tests/ --cov=etf_dashboard --cov-report=html
```

### 测试分类

#### 单元测试 (`tests/test_*.py`)
- 测试单个函数或方法
- 使用mock对象隔离依赖
- 快速执行，无外部依赖

#### 集成测试 (`tests/integration/`)
- 测试组件间交互
- 可能涉及外部服务
- 执行时间较长

#### 端到端测试 (`tests/e2e/`)
- 测试完整用户流程
- 使用真实数据和服务
- 在CI/CD中定期运行

## 📝 文档贡献

### 文档类型
- **README.md**: 项目概述和快速开始
- **API文档**: 代码中的文档字符串
- **用户指南**: 详细使用说明
- **开发文档**: 架构和开发指南

### 文档规范
- 使用Markdown格式
- 包含代码示例
- 添加适当的图表和截图
- 保持内容更新

## 🐛 Bug报告

### Bug报告模板

```markdown
## Bug描述
简洁清晰地描述bug

## 复现步骤
1. 进入 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

## 期望行为
清晰简洁地描述你期望发生什么

## 实际行为
描述实际发生了什么

## 环境信息
- OS: [e.g. Windows 10, macOS 11.0, Ubuntu 20.04]
- Python版本: [e.g. 3.8.5]
- 浏览器: [e.g. Chrome 91.0, Firefox 89.0]
- 项目版本: [e.g. v1.0.0]

## 附加信息
添加任何其他相关信息，如截图、日志等
```

## 💡 功能请求

### 功能请求模板

```markdown
## 功能描述
清晰简洁地描述你想要的功能

## 问题背景
这个功能解决什么问题？

## 解决方案
描述你希望的解决方案

## 替代方案
描述你考虑过的其他替代方案

## 附加信息
添加任何其他相关信息或截图
```

## 🏆 贡献者认可

我们重视每一个贡献，所有贡献者都会在以下地方得到认可：
- README.md 贡献者列表
- CHANGELOG.md 版本说明
- GitHub Contributors 页面

## 📞 获取帮助

如果您在贡献过程中遇到问题：

1. **查看文档**: 首先查看README和相关文档
2. **搜索Issue**: 查看是否有类似问题已被讨论
3. **创建Discussion**: 在GitHub Discussions中提问
4. **联系维护者**: 通过邮件联系项目维护者

## 📄 许可证

通过贡献代码，您同意您的贡献将在MIT许可证下授权。

---

再次感谢您的贡献！🎉