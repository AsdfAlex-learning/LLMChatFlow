from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from src.llm_system.server.schemas import ChatCompletionRequest, ChatCompletionResponse
from src.llm_system.engine.base import BaseEngine
import time
import json
import asyncio

router = APIRouter()

def get_engine(request: Request) -> BaseEngine:
    """
    从应用状态中获取 LLM 引擎实例。
    如果引擎未初始化，抛出 503 错误。
    """
    if not hasattr(request.app.state, "engine") or request.app.state.engine is None:
        raise HTTPException(status_code=503, detail="LLM 引擎未初始化")
    return request.app.state.engine

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, req: Request):
    """
    OpenAI 兼容的对话补全接口。
    支持流式 (stream=True) 和非流式响应。
    """
    engine = get_engine(req)
    
    messages = [msg.model_dump() for msg in request.messages]
    
    if request.stream:
        return StreamingResponse(
            stream_generator(engine, messages, request),
            media_type="text/event-stream"
        )
    else:
        try:
            # 在线程池中运行以避免阻塞事件循环
            response_data = await asyncio.to_thread(
                engine.chat_completion,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            return response_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

async def stream_generator(engine: BaseEngine, messages, request):
    """
    用于流式响应的异步生成器。
    """
    stream = engine.stream_chat_completion(
        messages=messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    # 为本次补全生成唯一 ID
    chunk_id = f"chatcmpl-{int(time.time())}"
    created = int(time.time())
    
    # 首先生成角色信息 (可选，但推荐)
    role_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
    }
    yield f"data: {json.dumps(role_chunk)}\n\n"
    
    # 在没有专用线程包装器的情况下迭代同步生成器有些棘手
    # 但由于 TextIteratorStreamer 使用了队列，迭代它非常快（只是从队列中弹出）。
    # 生成过程发生在 engine.stream_chat_completion 内部的独立线程中。
    # 所以我们可以直接迭代。
    
    for token in stream:
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        # 微小的休眠以允许上下文切换（如果需要），尽管对于快速 token 通常不是严格必要的
        await asyncio.sleep(0)
        
    # 生成结束标志
    finish_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    }
    yield f"data: {json.dumps(finish_chunk)}\n\n"
    yield "data: [DONE]\n\n"
