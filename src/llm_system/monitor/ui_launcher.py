import socket
import subprocess
import webbrowser
import time
import os
import sys

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def launch_mlflow_ui(port: int = 5000):
    """
    确保 MLflow UI 正在运行，并打开浏览器。
    """
    ui_url = f"http://localhost:{port}"
    
    if not is_port_in_use(port):
        print(f"正在启动 MLflow UI (端口 {port})...")
        try:
            # 尝试在后台启动 mlflow ui
            # 注意：这依赖于系统路径中有 mlflow 可执行文件
            subprocess.Popen(["mlflow", "ui", "--port", str(port)], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             shell=True)
            
            # 等待服务启动
            for _ in range(10):
                if is_port_in_use(port):
                    break
                time.sleep(1)
        except Exception as e:
            print(f"警告: 无法自动启动 MLflow UI: {e}")
            print(f"请手动运行 'mlflow ui' 并访问 {ui_url}")
            return
    else:
        print(f"检测到 MLflow UI 已在运行。")

    # 打开浏览器
    print(f"正在打开 MLflow UI: {ui_url}")
    try:
        webbrowser.open(ui_url)
    except Exception as e:
        print(f"无法自动打开浏览器: {e}")
