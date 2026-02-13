import argparse
import sys
import mlflow
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.llm_system.train.trainer import LLMTrainer
from src.llm_system.monitor.ui_launcher import launch_mlflow_ui

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="执行 LoRA 微调")
    parser.add_argument("--model_path", type=str, required=True, help="基础模型路径")
    parser.add_argument("--data_path", type=str, default="data/sft/sft_train.jsonl", help="训练数据路径")
    parser.add_argument("--output_dir", type=str, default="checkpoints/lora_v1", help="检查点输出目录")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch Size")

    args = parser.parse_args()
    
    # 启动 MLflow UI
    launch_mlflow_ui()

    # 确保 MLflow 在同一实验下记录
    mlflow.set_experiment(args.experiment_name)
    
    # Trainer 内部已经集成了 MLflow logging，但我们可以在外层再包一个 run 来记录特定的 meta info
    with mlflow.start_run(run_name="train_lora") as run:
        mlflow.log_params({
            "base_model": args.model_path,
            "data_path": args.data_path,
            "epochs": args.epochs
        })
        
        trainer = LLMTrainer(model_path=args.model_path, output_dir=args.output_dir)
        trainer.load_model_for_training(use_4bit=True)
        
        # [TODO: Integration] Training with Security-Filtered Data
        # ------------------------------------------------------------
        # Ensure that the training data (args.data_path) has been processed
        # by the security module (to remove unsafe content) and the skills module
        # (to include high-quality skill execution traces).
        #
        # See scripts/04_prepare_sft_data.py for the data preparation logic.
        #
        # Future enhancement:
        # Add a check here to verify data provenance or quality stats.
        # if not verify_data_quality(args.data_path):
        #     raise ValueError("Training data quality check failed")
        # ------------------------------------------------------------

        print("开始训练...")
        trainer.train(
            train_file=args.data_path,
            num_epochs=args.epochs,
            batch_size=args.batch_size
        )
        
        print(f"训练完成，模型已保存至 {args.output_dir}")
