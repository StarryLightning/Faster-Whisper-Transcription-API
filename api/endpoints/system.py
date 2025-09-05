# api/endpoints/system.py
from fastapi import APIRouter
from config.settings import SUPPORTED_MODELS, DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE, DEFAULT_BEAM_SIZE, \
    MODELS_DIR, DEFAULT_MAX_CONCURRENT, MIN_CONCURRENT_LIMIT, MAX_CONCURRENT_LIMIT, AUDIO_SLICE_CONFIG, \
    CONCURRENCY_CONFIG

router = APIRouter(tags=["system"])

@router.get("/")
async def root():
    return {"message": "Faster-Whisper Transcription API", "status": "running"}

@router.get("/health")
async def health():
    return {"status": "healthy"}

@router.get("/models")
async def list_models():
    """返回当前服务支持的模型列表"""
    return {"available_models": SUPPORTED_MODELS}

@router.get("/config")
async def get_config():
    """返回当前服务配置"""
    return {
        "default_model": DEFAULT_MODEL,
        "default_device": DEFAULT_DEVICE,
        "default_compute_type": DEFAULT_COMPUTE_TYPE,
        "default_beam_size": DEFAULT_BEAM_SIZE,
        "models_directory": MODELS_DIR,
        "batch_processing": {
            "default_max_concurrent": DEFAULT_MAX_CONCURRENT,
            "min_concurrent_limit": MIN_CONCURRENT_LIMIT,
            "max_concurrent_limit": MAX_CONCURRENT_LIMIT
        },
        "audio_slice_config": AUDIO_SLICE_CONFIG,
        "concurrency_config": CONCURRENCY_CONFIG
    }