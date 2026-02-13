import os
import torch
import logging
from typing import Optional, Dict, Any
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import (
    LoraConfig, 
    get_peft_model, 
    TaskType, 
    prepare_model_for_kbit_training
)
from datasets import load_dataset, Dataset
from src.llm_system.monitor.mlflow_logger import MLflowLogger

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMTrainer")

class LLMTrainer:
    def __init__(self, model_path: str, output_dir: str = "checkpoints"):
        """
        初始化训练器。
        
        :param model_path: 基础模型路径
        :param output_dir: 检查点保存目录
        """
        self.model_path = model_path
        self.output_dir = output_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        
        # 初始化 MLflow
        self.mlflow_logger = MLflowLogger()
        self.mlflow_logger.initialize()

    def load_model_for_training(self, use_4bit: bool = True):
        """
        加载模型并准备进行 LoRA 微调。
        """
        logger.info(f"正在加载训练模型: {self.model_path}, 4bit: {use_4bit}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # 量化配置
        bnb_config = None
        if use_4bit:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        # 准备 k-bit 训练
        if use_4bit:
            self.model = prepare_model_for_kbit_training(self.model)
            
        # LoRA 配置
        # 针对 Qwen/Llama 等常见模型的 target_modules
        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=8,
            lora_alpha=32,
            lora_dropout=0.1,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        )
        
        self.model = get_peft_model(self.model, peft_config)
        self.model.print_trainable_parameters()

    def train(self, 
              train_file: str, 
              eval_file: Optional[str] = None,
              batch_size: int = 4,
              num_epochs: int = 1,
              learning_rate: float = 2e-4):
        """
        开始训练。
        
        :param train_file: 训练数据文件路径 (json/jsonl)
        :param eval_file: 验证数据文件路径 (可选)
        """
        if not self.model:
            raise RuntimeError("模型未加载，请先调用 load_model_for_training")
            
        logger.info("加载数据集...")
        data_files = {"train": train_file}
        if eval_file:
            data_files["test"] = eval_file
            
        # 支持 json/jsonl 格式
        extension = train_file.split(".")[-1]
        raw_datasets = load_dataset(extension, data_files=data_files)
        
        # 数据预处理
        def process_func(example):
            # 简单的指令微调格式处理
            # 假设数据格式为 {"instruction": "...", "input": "...", "output": "..."}
            MAX_LENGTH = 512
            
            instruction = example.get('instruction', '')
            input_text = example.get('input', '')
            output_text = example.get('output', '')
            
            if input_text:
                prompt = f"Instruction: {instruction}\nInput: {input_text}\nOutput: "
            else:
                prompt = f"Instruction: {instruction}\nOutput: "
                
            full_text = prompt + output_text + self.tokenizer.eos_token
            
            tokenized = self.tokenizer(
                full_text,
                truncation=True,
                max_length=MAX_LENGTH,
                padding="max_length"
            )
            
            # 设置 labels，使得只计算 output 部分的 loss (可选，此处简单处理计算全文)
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized

        tokenized_datasets = raw_datasets.map(process_func, batched=False)
        
        # 训练参数
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            num_train_epochs=num_epochs,
            logging_steps=10,
            save_steps=50,
            evaluation_strategy="steps" if eval_file else "no",
            eval_steps=50 if eval_file else None,
            fp16=True,
            optim="paged_adamw_32bit",
            report_to="mlflow"
        )
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_datasets["train"],
            eval_dataset=tokenized_datasets.get("test"),
            data_collator=DataCollatorForSeq2Seq(tokenizer=self.tokenizer, padding=True),
        )
        
        logger.info("开始训练...")
        trainer.train()
        
        logger.info(f"训练完成，保存模型至 {self.output_dir}")
        trainer.save_model(self.output_dir)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM 微调脚本")
    parser.add_argument("--model_path", type=str, required=True, help="基础模型路径")
    parser.add_argument("--data_path", type=str, required=True, help="训练数据路径")
    parser.add_argument("--output_dir", type=str, default="lora_output", help="输出目录")
    
    args = parser.parse_args()
    
    trainer = LLMTrainer(model_path=args.model_path, output_dir=args.output_dir)
    trainer.load_model_for_training(use_4bit=True)
    trainer.train(train_file=args.data_path)
