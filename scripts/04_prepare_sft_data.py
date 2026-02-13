import json
import argparse
import mlflow
import os
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.llm_system.monitor.ui_launcher import launch_mlflow_ui

def prepare_sft_data(input_file: str, output_file: str, min_score: float = 4.0):
    """
    筛选高质量数据并转换为 SFT 格式 (JSONL)
    """
    print(f"正在处理数据: {input_file}")
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sft_data = []
    
    for item in data:
        scores = item.get("scores", {})
        
        # [SAFETY] Future Filter
        # 获取安全标记 (默认 unknown)，未来可在此处添加过滤逻辑
        # 例如: if item.get("safety_flag") == "unsafe": continue
        safety_flag = item.get("safety_flag", "unknown")
        
        # [TODO: Integration] Advanced Filtering based on Skills & Security
        # ------------------------------------------------------------
        # 1. Filter Unsafe Content
        # if safety_flag in ["DENY", "unsafe"]:
        #     continue
        #
        # 2. Prefer Skill-Generated Content
        # if item.get("source") == "skill":
        #     # Skill outputs are deterministic and high-quality, always include them
        #     # regardless of judge score (or with lower threshold)
        #     pass
        # ------------------------------------------------------------
        
        # 简单策略：准确性和有用性都大于阈值
        if scores.get("accuracy", 0) >= min_score and scores.get("helpfulness", 0) >= min_score:
            # 构造 Instruction Tuning 格式
            # 假设格式: {"instruction": "...", "input": "...", "output": "..."}
            sft_item = {
                "instruction": item["user"],
                "input": "",
                "output": item["assistant"]
            }
            sft_data.append(sft_item)
            
    print(f"筛选出 {len(sft_data)} / {len(data)} 条高质量数据")
    
    # 保存为 JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        for item in sft_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    return len(sft_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="准备 SFT 训练数据")
    parser.add_argument("--input_file", type=str, default="data/evaluations/evaluation_results.json", help="评测结果文件")
    parser.add_argument("--output_file", type=str, default="data/sft/sft_train.jsonl", help="输出 SFT 数据文件")
    parser.add_argument("--min_score", type=float, default=4.0, help="最低分数阈值")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")

    args = parser.parse_args()
    
    # 启动 MLflow UI
    launch_mlflow_ui()

    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="prepare_sft_data") as run:
        count = prepare_sft_data(args.input_file, args.output_file, args.min_score)
        
        mlflow.log_metric("dataset_size", count)
        mlflow.log_param("min_score_threshold", args.min_score)
        mlflow.log_artifact(args.output_file)
        
        print(f"数据准备完成，已保存至 {args.output_file}")
