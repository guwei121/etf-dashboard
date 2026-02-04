#!/usr/bin/env python3
"""
简单的应用停止脚本
"""

import os
import psutil
import subprocess

def stop_app():
    """停止ETF仪表盘应用"""
    print("🛑 停止ETF仪表盘...")
    
    stopped_count = 0
    
    # 1. 终止所有Python进程（包含streamlit或dashboard.py）
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline'] or []
                if any('streamlit' in str(arg) for arg in cmdline) or \
                   any('dashboard.py' in str(arg) for arg in cmdline):
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    stopped_count += 1
                    print(f"✅ 已停止进程 (PID: {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # 2. 使用taskkill作为备用方法
    try:
        result = subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 已使用taskkill终止Python进程")
    except Exception:
        pass
    
    # 3. 清理PID文件
    if os.path.exists('app.pid'):
        os.remove('app.pid')
        print("✅ 已清理PID文件")
    
    if stopped_count > 0:
        print(f"✅ 总共停止了 {stopped_count} 个进程")
    else:
        print("ℹ️ 没有找到运行中的应用进程")
    
    print("🎉 应用已完全停止")

if __name__ == "__main__":
    stop_app()