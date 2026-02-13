import argparse
import subprocess
import sys
import mlflow
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.config_loader import ConfigLoader
from src.llm_system.monitor.ui_launcher import launch_mlflow_ui

def rerun_evaluation(
    model_path: str,
    simulator_api_key: str,
    judge_api_key: str,
    output_prefix: str = "rerun"
):
    """
    串联运行模拟和评测脚本
    """
    python_exe = sys.executable
    
    # 1. 启动新模型的推理服务 (这步比较麻烦，因为需要后台运行)
    # 简单起见，这里假设用户手动启动了新模型的服务，或者我们只复用模拟和评测脚本
    # 实际场景下，应该在这里启动服务，等待就绪，然后运行脚本，最后关闭服务
    
    print("注意：请确保已加载微调后的模型启动了推理服务！")
    print("如果是 LoRA 模型，需要先合并权重或在加载时指定 Adapter。")
    print("本脚本仅演示重新运行模拟和评测流程。")
    
    # 2. 运行模拟
    sim_output = f"data/simulations/{output_prefix}_simulation.json"
    print("正在运行模拟对话...")
    subprocess.run([
        python_exe, "scripts/02_simulate_dialogue.py",
        "--simulator_api_key", simulator_api_key,
        "--output_file", sim_output,
        "--local_model", "finetuned-model" # 标识名称
    ], check=True)
    
    # 3. 运行评测
    eval_output = f"data/evaluations/{output_prefix}_evaluation.json"
    print("正在运行评测...")
    
    # [TODO: Integration] Metric Logging
    # ------------------------------------------------------------
    # Consider analyzing the evaluation results for Security metrics here
    # or inside 03_evaluate_responses.py
    # e.g., count of "safety_flag" == "DENY"
    # mlflow.log_metric("security_violation_count", count)
    # ------------------------------------------------------------
    
    subprocess.run([
        python_exe, "scripts/03_evaluate_responses.py",
        "--judge_api_key", judge_api_key,
        "--input_file", sim_output,
        "--output_file", eval_output
    ], check=True)
    
    return eval_output

if __name__ == "__main__":
    # 启动 MLflow UI
    launch_mlflow_ui()

    # 加载系统配置
    config_loader = ConfigLoader()
    llm_config = config_loader.system_config.llm
    default_api_key = llm_config.api_key

    parser = argparse.ArgumentParser(description="重跑评测流程")
    parser.add_argument("--model_path", type=str, required=True, help="微调后的模型路径")
    parser.add_argument("--api_key", type=str, default=default_api_key, help="DeepSeek API Key (默认从 config 读取)")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")
    
    args = parser.parse_args()
    
    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="rerun_evaluation_finetuned") as run:
        mlflow.log_param("finetuned_model_path", args.model_path)
        
        final_result_file = rerun_evaluation(
            args.model_path,
            args.api_key,
            args.api_key
        )
        
        mlflow.log_artifact(final_result_file)
        print("重测完成！")
