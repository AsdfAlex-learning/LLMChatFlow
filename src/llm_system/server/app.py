from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from src.llm_system.server.routers import router
from src.llm_system.engine.hf_runner import HFRunner
from src.llm_system.monitor.mlflow_logger import MLflowLogger
from src.core.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMServer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    logger.info("正在启动 LLM 服务...")
    
    # 初始化 MLflow
    mlflow_logger = MLflowLogger()
    mlflow_logger.initialize()
    
    # 初始化引擎
    config = ConfigLoader().system_config.llm_server
    model_path = config.model_path
    
    if not model_path:
        logger.warning("未配置 model_path。引擎将不会自动加载模型。")
        app.state.engine = HFRunner()
    else:
        logger.info(f"正在从 {model_path} 加载模型...")
        engine = HFRunner()
        try:
            # 读取配置中的量化标志
            load_in_4bit = config.load_in_4bit
            load_in_8bit = config.load_in_8bit
            
            engine.load_model(model_path, load_in_4bit=load_in_4bit, load_in_8bit=load_in_8bit)
            app.state.engine = engine
            logger.info("模型加载成功。")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            app.state.engine = None
    
    yield
    
    # 关闭阶段
    logger.info("正在关闭 LLM 服务...")
    # 如有需要，在此清理资源

app = FastAPI(title="本地 LLM API", version="1.0.0", lifespan=lifespan)

app.include_router(router)

@app.get("/health")
def health_check():
    """
    健康检查接口。
    """
    engine_status = "ready" if hasattr(app.state, "engine") and app.state.engine and app.state.engine.model else "not_ready"
    return {"status": "ok", "engine": engine_status}

if __name__ == "__main__":
    import uvicorn
    config = ConfigLoader().system_config.llm_server
    host = config.host
    port = config.port
    uvicorn.run(app, host=host, port=port)
