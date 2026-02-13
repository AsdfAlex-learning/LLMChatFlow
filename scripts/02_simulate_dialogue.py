import os
import sys
import argparse
import mlflow
import json
import time
import glob
from typing import List, Dict
from openai import OpenAI
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.core.config_loader import ConfigLoader
from src.core.utils import get_clean_api_base
from src.llm_system.monitor.ui_launcher import launch_mlflow_ui

def simulate_conversation(
    client_local: OpenAI, 
    client_simulator: OpenAI, 
    simulator_model: str, 
    local_model: str,
    topics: List[str],
    local_system_prompt: str,
    turns: int = 5
):
    """
    模拟对话过程
    """
    dialogue_data = []

    for topic in topics:
        print(f"--- 开始模拟话题: {topic} ---")
        
        # [PROMPT] AI Service Provider (Simulator) - System Prompt
        # 这里定义了模拟器（通常是高性能 AI 服务商模型，如 DeepSeek/OpenAI）的角色
        simulator_system_prompt = f"""
        你是一个温柔，性格随和的学长，正主动找心仪的学弟搭话聊天。
        当前想聊的话题是：{topic}。
        请顺着这个话题自然开启对话，语气轻松又不刻意，每次只说一句话，像真实和学弟通过即时通信软件聊天的感觉，会顺着话题轻轻追问或接话。
        """
        
        # 本地模型的 System Prompt (使用传入的配置)
        # local_system_prompt 已作为参数传入
        
        history_local = [{"role": "system", "content": local_system_prompt}]
        history_simulator = [{"role": "system", "content": simulator_system_prompt}]
        
        # [API CALL] AI Service Provider (Simulator)
        # 模拟器先发起话题
        simulator_response = client_simulator.chat.completions.create(
            model=simulator_model,
            messages=history_simulator
        )
        user_input = simulator_response.choices[0].message.content
        print(f"User (Sim): {user_input}")
        
        history_simulator.append({"role": "assistant", "content": user_input}) # 模拟器认为自己是 assistant (实际是 user 角色)
        history_local.append({"role": "user", "content": user_input})
        
        current_dialogue = {
            "topic": topic,
            "turns": []
        }
        
        # [TODO: Integration] Security & Skills Module Integration Point
        # ------------------------------------------------------------
        # from src.security import InputGuard, SecurityPolicy, SafetyDecision
        # from src.skills import RouterHelper
        #
        # 1. Initialize Guards (once outside loop)
        # policy = SecurityPolicy.default()
        # input_guard = InputGuard()
        #
        # 2. Input Guard Check
        # security_result = input_guard.check_input(user_input, policy)
        # if security_result.decision == SafetyDecision.DENY:
        #     assistant_output = "Sorry, I cannot handle this request due to safety policy."
        #     # Skip LLM generation
        #
        # 3. Skill Routing
        # skill_name = RouterHelper.match_intent(user_input) # Needs intent recognition first
        # if skill_name:
        #     success, skill_result = RouterHelper.dispatch(skill_name, context)
        #     if success:
        #         assistant_output = skill_result["display_text"]
        #         # Skip LLM generation
        # ------------------------------------------------------------

        for _ in range(turns):
            # 1. 本地模型生成回答
            start_time = time.time()
            try:
                local_response = client_local.chat.completions.create(
                    model=local_model,
                    messages=history_local
                )
                assistant_output = local_response.choices[0].message.content
            except Exception as e:
                print(f"Local Model Error: {e}")
                break
            latency = time.time() - start_time
            print(f"AI (Local): {assistant_output}")
            
            # [TODO: Integration] Output Guard Check
            # ------------------------------------------------------------
            # from src.security import OutputGuard
            # output_guard = OutputGuard()
            #
            # out_result = output_guard.check_output(assistant_output, policy)
            # if out_result.decision == SafetyDecision.DOWNGRADE:
            #     assistant_output = "[Filtered] " + out_result.reason
            # elif out_result.decision == SafetyDecision.REQUIRE_FALLBACK:
            #     # Call Fallback Model
            #     pass
            # ------------------------------------------------------------
            
            history_local.append({"role": "assistant", "content": assistant_output})
            history_simulator.append({"role": "user", "content": assistant_output})
            
            # 记录这一轮
            current_dialogue["turns"].append({
                "user": user_input,
                "assistant": assistant_output,
                "latency": latency
            })
            
            # 2. 模拟器生成下一句追问
            try:
                # [API CALL] AI Service Provider (Simulator)
                # 调用模拟器生成用户的追问
                simulator_response = client_simulator.chat.completions.create(
                    model=simulator_model,
                    messages=history_simulator
                )
                user_input = simulator_response.choices[0].message.content
            except Exception as e:
                print(f"Simulator Error: {e}")
                break
                
            print(f"User (Sim): {user_input}")
            
            history_simulator.append({"role": "assistant", "content": user_input})
            history_local.append({"role": "user", "content": user_input})
            
        dialogue_data.append(current_dialogue)
        
    return dialogue_data

if __name__ == "__main__":
    # 启动 MLflow UI
    launch_mlflow_ui()

    # 加载系统配置
    config_loader = ConfigLoader()
    llm_config = config_loader.system_config.llm
    
    default_api_key = llm_config.api_key
    default_api_base = get_clean_api_base(llm_config.api_url)
    default_model = llm_config.model

    parser = argparse.ArgumentParser(description="模拟对话并记录到 MLflow")
    parser.add_argument("--local_api_base", type=str, default="http://localhost:8000/v1", help="本地模型 API 地址")
    parser.add_argument("--local_api_key", type=str, default="sk-dummy", help="本地模型 API Key")
    parser.add_argument("--simulator_api_base", type=str, default=default_api_base, help="模拟器 API 地址 (默认从 config 读取)")
    parser.add_argument("--simulator_api_key", type=str, default=default_api_key, help="模拟器 API Key (默认从 config 读取)")
    parser.add_argument("--simulator_model", type=str, default=default_model, help="模拟器模型名称 (默认从 config 读取)")
    parser.add_argument("--local_model", type=str, default="local-model", help="本地模型名称")
    parser.add_argument("--output_file", type=str, default="data/simulations/simulation_data.json", help="输出文件路径")
    parser.add_argument("--experiment_name", type=str, default="LLM_Bootstrap", help="MLflow 实验名称")
    parser.add_argument("--topic_file", type=str, default="data/topics/topics_zh_general.txt", help="单个话题文件路径 (默认)")
    parser.add_argument("--topics_dir", type=str, default=None, help="话题文件目录 (若指定则加载目录下所有txt，覆盖单个文件设置)")

    args = parser.parse_args()
    
    # 初始化客户端
    client_local = OpenAI(base_url=args.local_api_base, api_key=args.local_api_key)
    client_simulator = OpenAI(base_url=args.simulator_api_base, api_key=args.simulator_api_key)
    
    # 加载话题
    topics = []
    if args.topics_dir and os.path.exists(args.topics_dir):
        print(f"从目录加载话题: {args.topics_dir}")
        topic_files = glob.glob(os.path.join(args.topics_dir, "*.txt"))
        for topic_file in topic_files:
            try:
                with open(topic_file, "r", encoding="utf-8") as f:
                    file_topics = [line.strip() for line in f if line.strip()]
                    topics.extend(file_topics)
                print(f"从 {topic_file} 加载了 {len(file_topics)} 个话题")
            except Exception as e:
                print(f"无法读取话题文件 {topic_file}: {e}")
    elif args.topic_file and os.path.exists(args.topic_file):
        print(f"加载单个话题文件: {args.topic_file}")
        try:
            with open(args.topic_file, "r", encoding="utf-8") as f:
                topics = [line.strip() for line in f if line.strip()]
            print(f"加载了 {len(topics)} 个话题")
        except Exception as e:
             print(f"无法读取话题文件 {args.topic_file}: {e}")
    else:
        print(f"未指定有效的话题文件或目录，使用默认硬编码话题")
        topics = [
            "Python 编程中的装饰器",
            "如何制作红烧肉",
            "解释量子纠缠",
            "推荐几本好看的科幻小说"
        ]
    
    if not topics:
         print("警告: 未找到任何话题，使用默认话题")
         topics = ["你好", "介绍一下你自己"]

    # 构建本地模型的 System Prompt (基于项目配置)
    prompt_manager = config_loader.prompt_manager
    local_system_prompt = f"{prompt_manager.ai_rules.format()}\n\n{prompt_manager.persona.format()}"
    print(f"已加载本地模型 System Prompt，长度: {len(local_system_prompt)}")
    
    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="simulate_dialogue") as run:
        # 记录 System Prompt 到 MLflow
        mlflow.log_text(local_system_prompt, "local_system_prompt.txt")

        data = simulate_conversation(
            client_local, 
            client_simulator, 
            args.simulator_model, 
            args.local_model, 
            topics,
            local_system_prompt
        )
        
        # 保存数据
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # 记录 artifact
        mlflow.log_artifact(args.output_file)
        print(f"对话模拟完成，数据已保存至 {args.output_file} 并上传至 MLflow Run {run.info.run_id}")
