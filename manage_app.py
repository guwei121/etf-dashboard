#!/usr/bin/env python3
"""
ETF仪表盘应用管理脚本

提供启动、停止、重启和状态检查功能
"""

import os
import sys
import time
import signal
import psutil
import subprocess
import argparse
from pathlib import Path

class AppManager:
    """应用管理器"""
    
    def __init__(self):
        self.app_name = "ETF仪表盘"
        self.app_file = "etf_dashboard/app/dashboard.py"
        self.default_port = 8503
        self.pid_file = "app.pid"
    
    def start(self, port=None, background=False):
        """启动应用"""
        port = port or self.default_port
        
        # 检查端口是否被占用
        if self._is_port_in_use(port):
            print(f"❌ 端口 {port} 已被占用")
            self._show_port_usage(port)
            return False
        
        # 检查应用是否已经在运行
        if self._is_app_running():
            print(f"⚠️ {self.app_name} 已经在运行")
            return False
        
        print(f"🚀 启动 {self.app_name} (端口: {port})...")
        
        # 清除代理设置
        self._clear_proxy_settings()
        
        # 构建启动命令
        cmd = [
            sys.executable, '-m', 'streamlit', 'run',
            self.app_file,
            '--server.port', str(port),
            '--server.address', 'localhost',
            '--browser.gatherUsageStats', 'false'
        ]
        
        try:
            if background:
                # 后台运行
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                
                # 保存PID
                with open(self.pid_file, 'w') as f:
                    f.write(str(process.pid))
                
                print(f"✅ {self.app_name} 已在后台启动 (PID: {process.pid})")
                print(f"🌐 访问地址: http://localhost:{port}")
                print(f"📝 使用 'python manage_app.py stop' 停止应用")
                
                return True
            else:
                # 前台运行
                print(f"🌐 访问地址: http://localhost:{port}")
                print(f"⚠️ 使用 Ctrl+C 或 'python manage_app.py stop' 停止应用")
                
                process = subprocess.run(cmd)
                return process.returncode == 0
                
        except KeyboardInterrupt:
            print(f"\n👋 {self.app_name} 已停止")
            return True
        except Exception as e:
            print(f"❌ 启动失败: {str(e)}")
            return False
    
    def stop(self):
        """停止应用"""
        print(f"🛑 停止 {self.app_name}...")
        
        stopped_count = 0
        
        # 1. 尝试从PID文件停止
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if self._kill_process(pid):
                    stopped_count += 1
                    print(f"✅ 已停止进程 (PID: {pid})")
                
                os.remove(self.pid_file)
            except Exception as e:
                print(f"⚠️ 从PID文件停止失败: {str(e)}")
        
        # 2. 查找并停止所有相关进程
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline'] or []
                    if any('streamlit' in str(arg) for arg in cmdline) or \
                       any('dashboard.py' in str(arg) for arg in cmdline):
                        python_processes.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        for pid in python_processes:
            if self._kill_process(pid):
                stopped_count += 1
                print(f"✅ 已停止Python进程 (PID: {pid})")
        
        # 3. 释放端口
        self._kill_processes_on_ports([8501, 8502, 8503, 8504])
        
        if stopped_count > 0:
            print(f"✅ 已停止 {stopped_count} 个进程")
        else:
            print("ℹ️ 没有找到运行中的应用进程")
        
        return True
    
    def restart(self, port=None):
        """重启应用"""
        print(f"🔄 重启 {self.app_name}...")
        self.stop()
        time.sleep(2)  # 等待进程完全停止
        return self.start(port, background=True)
    
    def status(self):
        """检查应用状态"""
        print(f"📊 {self.app_name} 状态检查")
        print("=" * 40)
        
        # 检查进程
        running_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline'] or []
                    if any('streamlit' in str(arg) for arg in cmdline) or \
                       any('dashboard.py' in str(arg) for arg in cmdline):
                        running_processes.append({
                            'pid': proc.info['pid'],
                            'create_time': proc.info['create_time']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if running_processes:
            print(f"✅ 发现 {len(running_processes)} 个运行中的进程:")
            for proc in running_processes:
                create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(proc['create_time']))
                print(f"  - PID: {proc['pid']}, 启动时间: {create_time}")
        else:
            print("❌ 没有发现运行中的进程")
        
        # 检查端口占用
        print("\n🌐 端口占用情况:")
        for port in [8501, 8502, 8503, 8504]:
            if self._is_port_in_use(port):
                print(f"  - 端口 {port}: ✅ 被占用")
            else:
                print(f"  - 端口 {port}: ❌ 空闲")
        
        # 检查PID文件
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                print(f"\n📝 PID文件存在: {pid}")
                if psutil.pid_exists(pid):
                    print(f"  - 进程 {pid} 正在运行")
                else:
                    print(f"  - 进程 {pid} 不存在 (僵尸PID文件)")
            except Exception as e:
                print(f"\n⚠️ PID文件读取失败: {str(e)}")
        else:
            print("\n📝 PID文件不存在")
    
    def _is_app_running(self):
        """检查应用是否在运行"""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline'] or []
                    if any('streamlit' in str(arg) for arg in cmdline) and \
                       any('dashboard.py' in str(arg) for arg in cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def _is_port_in_use(self, port):
        """检查端口是否被占用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                return True
        return False
    
    def _show_port_usage(self, port):
        """显示端口占用情况"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                try:
                    proc = psutil.Process(conn.pid)
                    print(f"  占用进程: {proc.name()} (PID: {conn.pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    print(f"  占用进程: 未知 (PID: {conn.pid})")
    
    def _kill_process(self, pid):
        """终止进程"""
        try:
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                proc.terminate()
                
                # 等待进程终止
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    # 强制终止
                    proc.kill()
                    proc.wait(timeout=5)
                
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass
        return False
    
    def _kill_processes_on_ports(self, ports):
        """终止占用指定端口的进程"""
        for port in ports:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    self._kill_process(conn.pid)
    
    def _clear_proxy_settings(self):
        """清除代理设置"""
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        for var in proxy_vars:
            if var in os.environ:
                del os.environ[var]
        os.environ['NO_PROXY'] = '*'


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ETF仪表盘应用管理器")
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'], 
                       help='要执行的操作')
    parser.add_argument('--port', type=int, default=8503, 
                       help='应用端口号 (默认: 8503)')
    parser.add_argument('--background', action='store_true', 
                       help='在后台运行应用')
    
    args = parser.parse_args()
    
    manager = AppManager()
    
    if args.action == 'start':
        success = manager.start(args.port, args.background)
        sys.exit(0 if success else 1)
    elif args.action == 'stop':
        success = manager.stop()
        sys.exit(0 if success else 1)
    elif args.action == 'restart':
        success = manager.restart(args.port)
        sys.exit(0 if success else 1)
    elif args.action == 'status':
        manager.status()
        sys.exit(0)


if __name__ == "__main__":
    main()