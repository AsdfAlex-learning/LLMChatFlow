import mlflow
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("MLflowLogger")

class MLflowLogger:
    _instance = None

    def __new__(cls):
        # 单例模式确保全局只有一个 Logger 实例
        if cls._instance is None:
            cls._instance = super(MLflowLogger, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self, experiment_name: str = "llm_system", tracking_uri: Optional[str] = None):
        """
        初始化 MLflow。
        :param experiment_name: 实验名称
        :param tracking_uri: 跟踪服务器 URI（可选）
        """
        if self.initialized:
            return
        
        try:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            
            mlflow.set_experiment(experiment_name)
            self.initialized = True
            logger.info(f"MLflow 初始化成功，实验名称: {experiment_name}")
        except Exception as e:
            logger.warning(f"MLflow 初始化失败: {e}")

    def log_params(self, params: Dict[str, Any]):
        """
        记录参数。
        """
        if not self.initialized:
            return
        try:
            mlflow.log_params(params)
        except Exception as e:
            logger.warning(f"参数记录失败: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        记录指标。
        """
        if not self.initialized:
            return
        try:
            mlflow.log_metrics(metrics, step=step)
        except Exception as e:
            logger.warning(f"指标记录失败: {e}")

    def log_artifact(self, local_path: str):
        """
        记录文件（Artifact）。
        """
        if not self.initialized:
            return
        try:
            mlflow.log_artifact(local_path)
        except Exception as e:
            logger.warning(f"文件记录失败: {e}")
