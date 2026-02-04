#!/usr/bin/env python3
"""
简单的应用启动脚本
"""

import os
import sys
import subprocess

def start_app(port=8503):
    """启动ETF仪表盘应用"""
    print(f"🚀 启动ETF仪表盘 (端口: {port})...")
    
    # 清除代理设置
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
    os.environ['NO_PROXY'] = '*'
    print("✅ 已清除代理设置")
    
    # 构建启动命令
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        'etf_dashboard/main.py',
        '--server.port', str(port),
        '--server.address', 'localhost',
        '--browser.gatherUsageStats', 'false'
    ]
    
    print(f"🌐 访问地址: http://localhost:{port}")
    print("⚠️ 使用 Ctrl+C 停止应用，或运行 'python stop_app.py'")
    print("=" * 50)
    
    try:
        # 前台运行
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print(f"\n👋 ETF仪表盘已停止")
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动ETF仪表盘")
    parser.add_argument('--port', type=int, default=8503, help='端口号')
    args = parser.parse_args()
    
    start_app(args.port)