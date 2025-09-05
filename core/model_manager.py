# model_manager.py
import asyncio
import logging
from typing import Dict
from faster_whisper import WhisperModel

from core.model_loader import get_model, loaded_models, _model_load_lock

logger = logging.getLogger(__name__)

# 全局模型缓存
_model_cache: Dict[str, WhisperModel] = {}


async def get_cached_model(model_name: str, device: str, compute_type: str) -> WhisperModel:
    """
    获取缓存中的模型，如果不存在则加载并缓存
    """
    key = f"{model_name}_{device}_{compute_type}"

    # 快速检查缓存
    if key in loaded_models:
        logger.info(f"✅ 从缓存中获取模型: {key}")
        return loaded_models[key]

    logger.info(f"🔄 模型 {key} 未在缓存中，开始异步加载...")
    # 在线程池中执行原有的同步加载逻辑
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        get_model,
        model_name,
        device,
        compute_type
    )


def _load_model_sync(model_name: str, device: str, compute_type: str) -> WhisperModel:
    """同步加载模型的辅助函数"""
    return get_model(model_name, device, compute_type)


def clear_model_cache():
    """清空模型缓存"""
    with _model_load_lock:
        loaded_models.clear()
    logger.info("✅ 模型缓存已清空")


def get_cached_model_names() -> list:
    """获取当前缓存的所有模型名称"""
    return list(loaded_models.keys())