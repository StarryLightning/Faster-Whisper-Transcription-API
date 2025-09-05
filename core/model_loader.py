# core/model_loader.py
import os
from threading import Lock

from huggingface_hub import snapshot_download
from faster_whisper import WhisperModel
from config.settings import MODELS_DIR, DEVICE_COMPUTE_COMPATIBILITY

# 缓存已加载模型
loaded_models = {}
_model_load_lock = Lock()

def get_model(model_name: str, device: str, compute_type: str):
    """
    加载模型并缓存，自动下载缺失模型
    """
    # 验证设备和支持的精度
    if device not in DEVICE_COMPUTE_COMPATIBILITY:
        raise ValueError(f"不支持的设备: {device}。支持的设备: {list(DEVICE_COMPUTE_COMPATIBILITY.keys())}")

    if compute_type not in DEVICE_COMPUTE_COMPATIBILITY[device]:
        fallback_type = DEVICE_COMPUTE_COMPATIBILITY[device][0]
        print(f"[Warning] 设备 {device} 不支持 {compute_type}，已自动降级到 {fallback_type}。")
        compute_type = fallback_type

    # 生成缓存键
    key = f"{model_name}_{device}_{compute_type}"

    if key in loaded_models:
        return loaded_models[key]

    with _model_load_lock:
        if key not in loaded_models:
            model_dir_name = model_name.replace("/", "-")
            model_dir = os.path.join(MODELS_DIR, model_dir_name)

            # 自动下载模型
            if not os.path.exists(model_dir):
                os.makedirs(model_dir, exist_ok=True)
                print(f"正在下载模型 {model_name} 到 {model_dir}...")
                try:
                    snapshot_download(
                        repo_id=model_name,
                        local_dir=model_dir,
                        local_dir_use_symlinks=False,
                        resume_download=True,
                        token=None,
                    )
                    print(f"模型下载成功！存储于: {model_dir}")
                except Exception as e:
                    raise RuntimeError(f"模型 '{model_name}' 下载失败: {str(e)}") from e

            if not os.path.isdir(model_dir):
                raise RuntimeError(f"模型目录 {model_dir} 不存在")

            # 加载模型
            try:
                loaded_models[key] = WhisperModel(
                    model_dir,
                    device=device,
                    compute_type=compute_type,
                    local_files_only=True
                )
                print(f"成功加载模型: {key}")
            except Exception as e:
                raise RuntimeError(f"加载模型失败: {e}") from e

    return loaded_models[key]