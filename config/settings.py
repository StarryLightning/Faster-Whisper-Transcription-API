# config/settings.py

# 全局配置文件，默认为24核cpu的工作站级别主机，可自行修改参数

import os
# 工具函数：安全转换类型
def _int_env(key, default):
    value = os.getenv(key)
    return int(value) if value and value.isdigit() else default

def _float_env(key, default):
    value = os.getenv(key)
    return float(value) if value else default

def _bool_env(key, default):
    value = os.getenv(key)
    return value.lower() == "true" if value else default

# 1. 模型配置
DEFAULT_MODEL = os.getenv("MODEL_NAME", "faster-whisper-small")
DEFAULT_DEVICE = os.getenv("DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")
DEFAULT_BEAM_SIZE = _int_env("BEAM_SIZE", 5)
MODELS_DIR = os.getenv("MODELS_DIR", "./Models")

# 2. 支持的模型列表
SUPPORTED_MODELS = [
    "faster-whisper-small",
    "faster-whisper-large-v3-turbo",
]

# 3. 支持的音频格式
ALLOWED_AUDIO_TYPES = [
    "audio/wav", "audio/x-wav", "audio/wave", "audio/x-pn-wav",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a",
    "audio/flac", "audio/ogg", "audio/webm", "application/octet-stream"
]

# 4. 设备与精度兼容性配置
DEVICE_COMPUTE_COMPATIBILITY = {
    "cpu": ["float32", "int8"],
    "cuda": ["float16", "float32", "int8"]
}

# 5. 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = _int_env("PORT", 9898)
RELOAD = _bool_env("RELOAD", False)
WORKERS = _int_env("WORKERS", 18)  # 👈 由环境变量控制 Gunicorn worker 数

# 6.音频切片默认配置
AUDIO_SLICE_CONFIG = {
    "min_slice_length": _int_env("MIN_SLICE_LENGTH", 30000),      # 最小切片长度（毫秒）
    "max_slice_length": _int_env("MAX_SLICE_LENGTH", 120000),      # 最大切片长度（毫秒）
    "min_interval": _int_env("MIN_INTERVAL", 500),                # 最小静音间隔
    "threshold": _int_env("THRESHOLD", -40),                             # 静音阈值
    "hop_size": _int_env("HOP_SIZE", 20),                         # 跳数大小：20ms
    "max_sil_kept": _int_env("MAX_SIL_KEPT", 1000),               # 最大保留静音：1000ms
    "max_total_slices": _int_env("MAX_TOTAL_SLICES", 144),         # 最大切片数量限制
}

# 7.并发处理配置
CONCURRENCY_CONFIG = {
    "default_max_concurrent": _int_env("MAX_CONCURRENT", 2),
    "min_concurrent_limit": _int_env("MIN_CONCURRENT", 1),
    "max_concurrent_limit": _int_env("MAX_CONCURRENT_LIMIT", 3),
    "slices_per_thread": _int_env("SLICES_PER_THREAD", 4),
    "consider_system_load": _bool_env("CONSIDER_SYSTEM_LOAD", True),
}