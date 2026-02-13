import sys
import argparse
import mlflow
import uvicorn
import threading
import time
import requests
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.llm_system.monitor.mlflow_logger import MLflowLogger
from src.llm_system.monitor.ui_launcher import launch_mlflow_ui
from src.core.config_loader import ConfigLoader

def start_server(config):
    """
    启动本地推理服务
    """
    # [TODO: Integration] Security & Skills Module Initialization
    # ------------------------------------------------------------
    # If the server needs to enforce security policies or use skills directly:
    # 
    # from src.security import SecurityPolicy
    # from src.skills import SkillRegistry
    # 
    # # Initialize global components
    # SecurityPolicy.load_from_file("config/security_policy.yaml")
    # SkillRegistry.load_skills("src/skills/definitions")
    # 
    # # Pass these to the app instance or set as global singletons
    # # app.state.security_policy = ...
    # ------------------------------------------------------------

    # 使用 uvicorn 启动
    # 注意：在代码中直接运行 uvicorn.run 会阻塞，所以通常放在主线程
    # 但这里我们需要同时做一些 MLflow 的记录，所以可以用子进程或直接作为入口
    
    print(f"正在启动推理服务... 模型: {config.model_path}")
    uvicorn.run("src.llm_system.server.app:app", host=config.host, port=config.port, reload=False)

def check_server_health(url: str, max_retries: int = 30):
    """
    检查服务是否启动成功
    """
    print("等待服务启动...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/docs")
            if response.status_code == 200:
                print("服务已启动！")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动模型并记录 MLflow 实验")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")
    
    args = parser.parse_args()

    # 启动 MLflow UI
    launch_mlflow_ui()

    # 加载配置
    config = ConfigLoader().system_config.llm_server

    # 初始化 MLflow
    logger = MLflowLogger()
    mlflow.set_experiment(args.experiment_name)
    
    with mlflow.start_run(run_name="bootstrap_model") as run:
        # 记录参数
        mlflow.log_params({
            "model_path": config.model_path,
            "use_4bit": config.load_in_4bit,
            "host": config.host,
            "port": config.port
        })
        
        print(f"MLflow Run ID: {run.info.run_id}")
        print(f"Configuration loaded from system.yaml: {config.model_path}")
        
        # 启动服务
        try:
            start_server(config)
        except KeyboardInterrupt:
            print("服务已停止")
