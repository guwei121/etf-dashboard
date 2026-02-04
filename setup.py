"""
ETF投资仪表盘安装脚本

用于安装ETF投资仪表盘包及其依赖项。
支持开发模式安装和生产环境部署。
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "ETF投资仪表盘 - 基于规则的ETF投资决策支持系统"

# 读取requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # 过滤注释和空行
        requirements = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                requirements.append(line)
        return requirements
    return []

setup(
    name="etf-investment-dashboard",
    version="1.0.0",
    author="ETF Dashboard Team",
    author_email="team@etfdashboard.com",
    description="基于规则的ETF投资决策支持系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/etf-dashboard/etf-investment-dashboard",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "hypothesis>=6.68.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
            "jupyter>=1.0.0",
            "ipython>=8.0.0",
        ],
        "optional": [
            "ta-lib>=0.4.25",
            "numba>=0.56.0",
            "diskcache>=5.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "etf-dashboard=etf_dashboard.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "etf_dashboard": [
            "config/*.json",
            "templates/*.html",
            "static/*",
        ],
    },
    zip_safe=False,
    keywords="etf investment dashboard finance technical-analysis",
    project_urls={
        "Bug Reports": "https://github.com/etf-dashboard/etf-investment-dashboard/issues",
        "Source": "https://github.com/etf-dashboard/etf-investment-dashboard",
        "Documentation": "https://etf-dashboard.readthedocs.io/",
    },
)