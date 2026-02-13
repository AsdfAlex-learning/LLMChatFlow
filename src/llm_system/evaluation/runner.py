import os
import sys
import argparse
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess
import csv
import glob

from src.llm_system.monitor.mlflow_logger import MLflowLogger

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpenCompassWrapper")

class OpenCompassEvaluator:
    def __init__(self, 
                 model_path: str, 
                 work_dir: str = "eval_results",
                 datasets: List[str] = None):
        """
        初始化评估器。
        
        :param model_path: 模型路径
        :param work_dir: 工作目录，用于存储 OpenCompass 的输出
        :param datasets: 待评估的数据集列表 (OpenCompass 格式，如 'ceval_gen', 'mmlu_gen')
        """
        self.model_path = model_path
        self.work_dir = os.path.abspath(work_dir)
        self.datasets = datasets or ["ceval_gen", "mmlu_gen"]
        self.mlflow_logger = MLflowLogger()
        self.mlflow_logger.initialize()

    def generate_config(self, load_in_4bit: bool = True) -> str:
        """
        生成 OpenCompass 的 Python 配置文件。
        
        :param load_in_4bit: 是否开启 4bit 量化
        :return: 生成的配置文件路径
        """
        os.makedirs(self.work_dir, exist_ok=True)
        config_path = os.path.join(self.work_dir, "eval_config.py")
        
        # 转换数据集列表为 Python 代码字符串
        datasets_code = " + ".join([f"{d}" for d in self.datasets])
        
        # 导入语句 (OpenCompass 需要 dataset 定义)
        imports = []
        for d in self.datasets:
            # 这是一个简化的假设，假设数据集变量名与模块名一致
            # 实际使用中可能需要更复杂的映射，这里演示使用 ceval 和 mmlu
            if "ceval" in d:
                imports.append("from opencompass.datasets import ceval_datasets")
            elif "mmlu" in d:
                imports.append("from opencompass.datasets import mmlu_datasets")
            # 这里简单处理，OpenCompass 实际上通常通过 configs 导入
            # 为了稳健性，我们使用 OpenCompass 推荐的 config 引用方式
        
        # 构建配置内容
        # 注意：这里我们动态构建一个简单的配置
        config_content = f"""
from opencompass.models import HuggingFaceCausalLM

# 数据集配置
# 注意：为了简化，这里直接引用 OpenCompass 的预定义数据集变量
# 用户需要确保 OpenCompass 环境中包含这些定义
# 常用数据集: 'ceval_gen', 'mmlu_gen'
datasets = []
try:
    from opencompass.configs.datasets.ceval.ceval_gen import ceval_datasets
    datasets.extend(ceval_datasets)
except ImportError:
    pass

try:
    from opencompass.configs.datasets.mmlu.mmlu_gen import mmlu_datasets
    datasets.extend(mmlu_datasets)
except ImportError:
    pass

# 如果未找到默认数据集，则根据传入参数尝试加载 (此处为简化示例)
if not datasets:
    # 这里的回退逻辑视具体需求而定
    pass

# 模型配置
models = [
    dict(
        type=HuggingFaceCausalLM,
        abbr='target-model',
        path='{self.model_path.replace(os.sep, "/")}',
        tokenizer_path='{self.model_path.replace(os.sep, "/")}',
        model_kwargs=dict(
            device_map='auto',
            trust_remote_code=True,
            load_in_4bit={str(load_in_4bit)}
        ),
        tokenizer_kwargs=dict(
            padding_side='left',
            trust_remote_code=True,
        ),
        max_out_len=100,
        max_seq_len=2048,
        batch_size=4,
        run_cfg=dict(num_gpus=1, num_procs=1),
    )
]

# 运行配置
work_dir = '{self.work_dir.replace(os.sep, "/")}'
"""
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        logger.info(f"OpenCompass 配置文件已生成: {config_path}")
        return config_path

    def run_eval(self, config_path: str):
        """
        运行 OpenCompass 评测。
        """
        logger.info("开始运行 OpenCompass 评测...")
        
        # 使用 subprocess 调用 opencompass 命令
        # 假设 opencompass 已安装在环境中
        cmd = [sys.executable, "-m", "opencompass.cli.main", config_path, "-w", self.work_dir]
        
        try:
            # 实时打印输出
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            
            if process.returncode != 0:
                logger.error("OpenCompass 评测运行失败")
                raise RuntimeError("OpenCompass execution failed")
                
            logger.info("OpenCompass 评测完成")
            
        except Exception as e:
            logger.error(f"运行评测时发生错误: {e}")
            raise

    def parse_and_log_results(self):
        """
        解析结果并记录到 MLflow。
        OpenCompass 通常在 work_dir 下生成 summary 目录。
        """
        logger.info("正在解析评测结果...")
        
        # 查找最新的 csv 结果
        # 路径通常是 work_dir/timestamp/summary/summary_*.csv
        # 或者直接在 work_dir 下查找
        
        # 简单的查找逻辑：递归查找所有 csv
        csv_files = glob.glob(os.path.join(self.work_dir, "**", "*.csv"), recursive=True)
        if not csv_files:
            logger.warning("未找到结果 CSV 文件")
            return

        # 取最新的文件
        latest_csv = max(csv_files, key=os.path.getmtime)
        logger.info(f"找到结果文件: {latest_csv}")
        
        self.mlflow_logger.log_artifact(latest_csv)
        
        # 解析 CSV 并记录 Metrics
        try:
            with open(latest_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 假设 CSV 包含 'dataset' 和 'score' 等列
                    # OpenCompass 的输出格式可能变动，这里做一种通用的尝试
                    # 通常第一列是 dataset, 后面是 prompt version, metric, model_name...
                    
                    # 示例: dataset, version, metric, mode, target-model
                    # 我们需要找到 model 对应的列。我们在 config 中将 model abbr 设为 'target-model'
                    
                    dataset = row.get('dataset', 'unknown')
                    score = row.get('target-model', None)
                    
                    if score is not None:
                        try:
                            score_val = float(score)
                            metric_name = f"eval_{dataset}"
                            self.mlflow_logger.log_metrics({metric_name: score_val})
                            logger.info(f"记录指标: {metric_name} = {score_val}")
                        except ValueError:
                            pass # 不是数字，可能是表头或其他信息
                            
        except Exception as e:
            logger.error(f"解析结果 CSV 失败: {e}")

    def run(self, load_in_4bit: bool = True):
        """
        执行完整的评测流程。
        """
        config_path = self.generate_config(load_in_4bit=load_in_4bit)
        
        # 记录本次评测参数
        self.mlflow_logger.log_params({
            "model_path": self.model_path,
            "load_in_4bit": load_in_4bit,
            "datasets": str(self.datasets)
        })
        
        self.run_eval(config_path)
        self.parse_and_log_results()

if __name__ == "__main__":
    # 简单的 CLI 入口
    parser = argparse.ArgumentParser(description="运行 OpenCompass 评测")
    parser.add_argument("--model_path", type=str, required=True, help="HF 模型路径")
    parser.add_argument("--work_dir", type=str, default="eval_results", help="工作目录")
    parser.add_argument("--4bit", action="store_true", default=True, help="使用 4bit 量化")
    
    args = parser.parse_args()
    
    evaluator = OpenCompassEvaluator(
        model_path=args.model_path,
        work_dir=args.work_dir
    )
    
    evaluator.run(load_in_4bit=args.__dict__["4bit"])
