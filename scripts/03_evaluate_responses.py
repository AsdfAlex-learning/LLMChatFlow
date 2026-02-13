import os
import sys
import argparse
import mlflow
import json
from openai import OpenAI
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.config_loader import ConfigLoader
from src.core.utils import get_clean_api_base
from src.llm_system.monitor.ui_launcher import launch_mlflow_ui

def evaluate_responses(
    client_judge: OpenAI,
    judge_model: str,
    data_file: str,
    output_file: str
):
    """
    使用 LLM 作为裁判对对话进行评分
    """
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    evaluated_data = []
    
    for session in data:
        topic = session["topic"]
        print(f"--- 正在评估话题: {topic} ---")
        
        for turn in session["turns"]:
            user_input = turn["user"]
            assistant_output = turn["assistant"]
            
            # [PROMPT] AI Service Provider (Judge) - Evaluation Prompt
            # 构造评测 Prompt，发送给高性能模型（如 DeepSeek/OpenAI）进行打分
            prompt = f"""
            请作为一位公正的裁判，评估以下 AI 助手的回答质量。
            
            用户问题: {user_input}
            AI 回答: {assistant_output}
            
            请从以下维度进行评分 (1-5分):
            1. 准确性 (Accuracy)
            2. 有用性 (Helpfulness)
            3. 连贯性 (Coherence)
            
            请以 JSON 格式输出结果，包含 keys: accuracy, helpfulness, coherence, reasoning (简短理由)。
            """
            
            try:
                # [API CALL] AI Service Provider (Judge)
                # 调用裁判模型获取评分
                response = client_judge.chat.completions.create(
                    model=judge_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                score_json = json.loads(response.choices[0].message.content)
                
                # 合并结果
                evaluated_item = turn.copy()
                evaluated_item["scores"] = score_json
                evaluated_item["topic"] = topic
                
                # [SAFETY] Safety Module Hook
                # 预留安全模块接口，未来可在此处集成自动安全检测逻辑
                # 目前默认为 "unknown"，后续可扩展为 "safe", "unsafe", "sensitive" 等
                evaluated_item["safety_flag"] = "unknown"
                
                # [TODO: Integration] Automated Security Evaluation
                # ------------------------------------------------------------
                # from src.security import OutputGuard, SecurityPolicy
                #
                # output_guard = OutputGuard()
                # policy = SecurityPolicy.default() # Or use a stricter evaluation policy
                #
                # # Run security check on the generated response
                # sec_result = output_guard.check_output(assistant_output, policy)
                #
                # # Update safety_flag based on actual decision
                # evaluated_item["safety_flag"] = sec_result.decision.name
                # evaluated_item["security_metadata"] = sec_result.to_dict()
                # ------------------------------------------------------------
                
                evaluated_data.append(evaluated_item)
                
                print(f"Scores: {score_json}")
                
            except Exception as e:
                print(f"Evaluation Error: {e}")
                
    return evaluated_data

if __name__ == "__main__":
    # 启动 MLflow UI
    launch_mlflow_ui()

    # 加载系统配置
    config_loader = ConfigLoader()
    llm_config = config_loader.system_config.llm
    
    default_api_key = llm_config.api_key
    default_api_base = get_clean_api_base(llm_config.api_url)
    default_model = llm_config.model

    parser = argparse.ArgumentParser(description="评估对话质量并记录到 MLflow")
    parser.add_argument("--judge_api_base", type=str, default=default_api_base, help="裁判 API 地址 (默认从 config 读取)")
    parser.add_argument("--judge_api_key", type=str, default=default_api_key, help="裁判 API Key (默认从 config 读取)")
    parser.add_argument("--judge_model", type=str, default=default_model, help="裁判模型名称 (默认从 config 读取)")
    parser.add_argument("--input_file", type=str, default="data/simulations/simulation_data.json", help="输入数据文件")
    parser.add_argument("--output_file", type=str, default="data/evaluations/evaluation_results.json", help="输出结果文件")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")

    args = parser.parse_args()
    
    client_judge = OpenAI(base_url=args.judge_api_base, api_key=args.judge_api_key)
    
    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="evaluate_responses") as run:
        results = evaluate_responses(
            client_judge,
            args.judge_model,
            args.input_file,
            args.output_file
        )
        
        # 保存结果
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        # 计算平均分
        avg_accuracy = sum([item["scores"]["accuracy"] for item in results]) / len(results) if results else 0
        avg_helpfulness = sum([item["scores"]["helpfulness"] for item in results]) / len(results) if results else 0
        
        # 记录 Metrics
        mlflow.log_metrics({
            "avg_accuracy": avg_accuracy,
            "avg_helpfulness": avg_helpfulness
        })
        
        # 记录 Artifact
        mlflow.log_artifact(args.output_file)
        print(f"评估完成，结果已保存至 {args.output_file} 并上传至 MLflow Run {run.info.run_id}")
