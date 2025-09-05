# api/endpoints/system.py
from fastapi import APIRouter
from config.settings import SUPPORTED_MODELS, DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE, DEFAULT_BEAM_SIZE, \
    MODELS_DIR, AUDIO_SLICE_CONFIG, \
    CONCURRENCY_CONFIG
from core.model_manager import get_cached_model_names

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

@router.get("/model-cache/status")
async def get_model_cache_status():
    """获取模型缓存状态"""
    return {
        "cached_models": get_cached_model_names(),
        "cache_size": len(get_cached_model_names())
    }

@router.post("/model-cache/clear")
async def clear_model_cache():
    """清空模型缓存"""
    clear_model_cache()
    return {"message": "模型缓存已清空"}

@router.get("/config")
async def get_config():
    """返回当前服务配置"""
    return {
        "default_model": DEFAULT_MODEL,
        "default_device": DEFAULT_DEVICE,
        "default_compute_type": DEFAULT_COMPUTE_TYPE,
        "default_beam_size": DEFAULT_BEAM_SIZE,
        "models_directory": MODELS_DIR,
        "audio_slice_config": AUDIO_SLICE_CONFIG,
        "concurrency_config": CONCURRENCY_CONFIG
    }