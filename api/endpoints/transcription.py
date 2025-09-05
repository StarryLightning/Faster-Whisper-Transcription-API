import asyncio
import logging
import os
import tempfile
from typing import List

import librosa
from fastapi import APIRouter, UploadFile, File, Query

from config.settings import SUPPORTED_MODELS, DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE, \
    DEFAULT_BEAM_SIZE, MIN_CONCURRENT_LIMIT, MAX_CONCURRENT_LIMIT
from core.MyThreadPool import executor
from core.model_loader import get_model
from core.processing_strategy import determine_processing_strategy, process_batch_strategy, process_slice_strategy, process_mixed_strategy
from config.response_schema import ApiResponse

router = APIRouter(tags=["transcription"])

# 配置日志
logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/transcribe")
async def transcribe(
        files: List[UploadFile] = File(..., description="音频文件列表（支持混合类型）"),
        model_name: str = Query(DEFAULT_MODEL, description="HuggingFace模型仓库ID"),
        beam_size: int = Query(DEFAULT_BEAM_SIZE, description="Beam Size"),
        device: str = Query(DEFAULT_DEVICE, description="运行设备: cpu/cuda"),
        compute_type: str = Query(DEFAULT_COMPUTE_TYPE, description="计算精度"),
        language: str = Query(None, description="指定语言代码（如zh、en），可选"),
        auto_slice: bool = Query(True, description="是否自动启用音频切片优化（处理多个长音频文件推荐关闭）"),
        max_concurrent: int = Query(None, ge=MIN_CONCURRENT_LIMIT, le=MAX_CONCURRENT_LIMIT, description="最大并发处理数（推荐让系统自动计算）"),
        consider_system_load: bool = Query(True, description="是否考虑系统当前负载")
):

    logger.info(f"开始智能转录处理，文件数量: {len(files)}，自动切片: {auto_slice}")
    #验证模型是否支持
    if model_name not in SUPPORTED_MODELS:
        return ApiResponse.error_response(f"不支持的模型。请选择支持的模型: {', '.join(SUPPORTED_MODELS)}", 400)

    if not files:
        return ApiResponse.error_response("请至少上传一个文件", 400)

    # 保存临时文件
    file_infos = []
    try:
        for file in files:
            suffix = "." + file.filename.split('.')[-1] if '.' in file.filename else ".wav"
            with tempfile.NamedTemporaryFile(delete =  False, suffix = suffix) as tmp:
                contents = await file.read()
                tmp.write(contents)

                #分析音频特性
                duration = librosa.get_duration(filename = tmp.name)
                file_type = "long" if duration > 300 else "short" #大于5分钟判定为长音频

                file_infos.append({
                    "filename": file.filename,
                    "path": tmp.name,
                    "content_type": file.content_type,
                    "duration": duration,
                    "type": file_type,
                    "requires_slicing": auto_slice and duration > 480  # 8分钟以上建议切片
                })

        # 预先加载模型
        loop = asyncio.get_running_loop()
        model = await loop.run_in_executor(executor, get_model, model_name, device, compute_type)

        #智能路由决策
        processing_strategy = await determine_processing_strategy(file_infos, auto_slice)
        logger.info(f"选择处理策略: {processing_strategy}")
        if processing_strategy == "batch_only":
            response_data = await process_batch_strategy(file_infos, model, beam_size, language, max_concurrent)
        elif processing_strategy == "slice_only":
            response_data = await process_slice_strategy(file_infos[0], model, beam_size, language, max_concurrent, consider_system_load)
        else:
            response_data = await process_mixed_strategy(file_infos, model, beam_size, language, max_concurrent, consider_system_load)

        return ApiResponse.success_response(data = response_data, message = "转录音频成功")

    except Exception as e:
        logger.error(f"智能转录失败: {e}")
        return ApiResponse.error_response(f"处理失败: {str(e)}", 500)

    finally:
        # 清理临时文件
        for file_info in file_infos:
            if os.path.exists(file_info["path"]):
                try:
                    os.unlink(file_info["path"])
                except Exception as e:
                    logger.warning(f"清理文件失败 {file_info['path']}: {e}")