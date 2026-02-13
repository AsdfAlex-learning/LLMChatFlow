import torch 
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextIteratorStreamer
from typing import List, Dict, Any, Optional, Generator
from threading import Thread
import logging
from src.llm_system.engine.base import BaseEngine

logger = logging.getLogger("HFRunner")

class HFRunner(BaseEngine):
    def __init__(self):
        self.tokenizer = None
        self.model = None
        # 自动检测设备：如果有 CUDA 则使用，否则使用 CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self, model_path: str, load_in_4bit: bool = True, load_in_8bit: bool = False, **kwargs) -> None:
        """
        使用 HuggingFace Transformers 加载模型。
        支持 4-bit 和 8-bit 量化以节省显存。
        """
        logger.info(f"正在加载模型: {model_path}, 设备: {self.device}, 4bit量化: {load_in_4bit}, 8bit量化: {load_in_8bit}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            
            # 配置量化参数
            quantization_config = None
            if load_in_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            elif load_in_8bit:
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)

            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                quantization_config=quantization_config,
                device_map="auto" if (load_in_4bit or load_in_8bit) else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
                **kwargs
            )
            
            # 如果没有使用量化，则手动将模型移动到指定设备
            if not (load_in_4bit or load_in_8bit):
                self.model.to(self.device)
                
            self.model.eval()
            logger.info("模型加载成功。")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise e

    def generate(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7, **kwargs) -> str:
        """
        简单的文本生成函数。
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("模型未加载。请先调用 load_model。")

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.pad_token_id,
                **kwargs
            )
            
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # 如果模型回显了输入提示词（raw generation 中常见），则去除它
        if response.startswith(prompt):
            response = response[len(prompt):]
        return response.strip()

    def chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.7, **kwargs) -> Dict[str, Any]:
        """
        使用 Tokenizer 的聊天模板进行对话补全。
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("模型未加载。")

        # 应用聊天模板
        try:
            prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception as e:
            # 如果模板失败或不存在，使用简单的拼接作为回退
            logger.warning(f"应用聊天模板失败: {e}。将使用简单拼接。")
            prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt += f"{role}: {content}\n"
            prompt += "assistant: "

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.pad_token_id,
                **kwargs
            )
        
        # 只解码新生成的 tokens
        input_len = inputs.input_ids.shape[1]
        generated_tokens = outputs[0][input_len:]
        response_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        return {
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": input_len,
                "completion_tokens": len(generated_tokens),
                "total_tokens": input_len + len(generated_tokens)
            }
        }

    def _get_stop_criteria(self, stop_strings: List[str] = None):
        """
        构建停止条件。
        注意：Transformers 的 StoppingCriteria 比较复杂，这里实现一个简单的基于 stream 后处理的逻辑，
        或者在 generate 中使用 stopping_criteria 参数。
        为了简化，这里暂时不深入实现自定义 StoppingCriteria 类，而是依赖 tokenizer.eos_token_id。
        如果需要支持 stop_strings，建议在 stream 输出时进行截断。
        """
        # TODO: 实现基于字符串的停止条件
        return None

    def stream_chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.7, stop: List[str] = None, **kwargs) -> Generator[str, None, None]:
        """
        流式对话补全。
        使用 TextIteratorStreamer 实现流式输出。
        """
        if not self.model or not self.tokenizer:
            raise RuntimeError("模型未加载。")

        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True if temperature > 0 else False,
            pad_token_id=self.tokenizer.pad_token_id,
            **kwargs
        )
        
        # 补充：如果传入了 stop 参数，虽然 Transformers 原生不支持 list[str] 作为 stop，
        # 但我们可以在 yield 阶段进行简单的截断处理。
        
        # 在新线程中运行生成过程，以免阻塞
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        # 从 streamer 中产生输出
        for new_text in streamer:
            # 简单的停止词检查 (注意：这可能会切断部分输出)
            if stop:
                for s in stop:
                    if s in new_text:
                        new_text = new_text.split(s)[0]
                        yield new_text
                        return
            yield new_text
