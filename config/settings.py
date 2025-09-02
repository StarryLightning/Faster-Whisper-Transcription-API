# config/settings.py

# 1. 模型配置
DEFAULT_MODEL = "faster-whisper-small"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 5
MODELS_DIR = "./Models"
MAX_WORKERS = 4

# 2. 支持的模型列表
SUPPORTED_MODELS = [
    "Systran/faster-whisper-tiny",
    "Systran/faster-whisper-tiny.en",
    "Systran/faster-whisper-base",
    "Systran/faster-whisper-base.en",
    "Systran/faster-whisper-small",
    "Systran/faster-whisper-small.en",
    "Systran/faster-whisper-medium",
    "Systran/faster-whisper-medium.en",
    "Systran/faster-whisper-large-v1",
    "Systran/faster-whisper-large-v2",
    "Systran/faster-whisper-large-v3",
    "faster-whisper-small",
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
HOST = "0.0.0.0"
PORT = 9898
RELOAD = False
WORKERS = 2

# 6. 批量处理配置
DEFAULT_MAX_CONCURRENT = 4  # 默认最大并发数
MIN_CONCURRENT_LIMIT = 1
MAX_CONCURRENT_LIMIT = 10   # 最大并发数限制

# 7.音频切片默认配置
AUDIO_SLICE_CONFIG = {
    "min_slice_length": 120000,      # 最小切片长度
    "max_slice_length": 600000,     # 最大切片长度
    "min_interval": 500,            # 最小静音间隔：500ms
    "threshold": -40,               # 静音阈值：-35dB
    "hop_size": 20,                 # 跳数大小：20ms
    "max_sil_kept": 1000,           # 最大保留静音：1000ms
    "max_total_slices": 50,         # 最大切片数量限制
}

# 8.切片并发处理配置
CONCURRENCY_CONFIG = {
    "default_max_concurrent": 4,    # 默认最大并发数
    "min_concurrent_limit": 2,      # 最小并发数限制
    "max_concurrent_limit": 8,      # 最大并发数限制
    "slices_per_thread": 3,         # 每个线程处理的切片数
    "consider_system_load": True,   # 是否考虑系统负载
}