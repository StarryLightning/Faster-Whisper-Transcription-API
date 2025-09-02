# api/app.py
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor

from config.settings import DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE, MAX_WORKERS, MODELS_DIR
from core.model_loader import get_model
from api.endpoints import system, transcription

# 全局线程池
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期管理"""
    print("🚀 Faster-Whisper API 服务启动中...")
    print(f"📁 模型存储目录: {MODELS_DIR}")
    print(f"🔧 默认配置: device={DEFAULT_DEVICE}, compute_type={DEFAULT_COMPUTE_TYPE}")

    try:
        # 预热默认模型
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, get_model, DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE)
        print("✅ 默认模型预热加载完成！")
    except Exception as e:
        print(f"⚠️  模型预热失败: {e}。服务仍可启动，但首次请求可能会较慢。")

    yield  # 应用在此运行

    # shutdown
    print("🛑 服务关闭中...")
    executor.shutdown(wait=True)

# 创建FastAPI应用
app = FastAPI(
    title="Faster-Whisper FastAPI 接口",
    description="基于Faster-Whisper的语音转录API服务，支持单文件和批量处理",
    version="1.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(system.router)
app.include_router(transcription.router, prefix="/api/v1")