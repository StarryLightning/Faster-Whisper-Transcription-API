import logging
import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import librosa
from fastapi import APIRouter, UploadFile, File, Query

from config.settings import SUPPORTED_MODELS, ALLOWED_AUDIO_TYPES, DEFAULT_MODEL, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE, \
    DEFAULT_BEAM_SIZE, MAX_WORKERS, DEFAULT_MAX_CONCURRENT, MIN_CONCURRENT_LIMIT, MAX_CONCURRENT_LIMIT, \
    AUDIO_SLICE_CONFIG
from core.model_loader import get_model
from core.slice_tools.merge_slice import merge_large_slices
from core.transcriber import transcribe_audio
from core.audio_slicer import slice_audio_file, cleanup_slices
from core.slice_tools.concurrency_optimizer import calculate_optimal_concurrency, concurrency_optimizer
from core.slice_tools.process_slice import process_slice, aggregate_results
from config.response_schema import ApiResponse

router = APIRouter(tags=["transcription"])
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

@router.post("/transcribe-batch")
async def transcribe_batch(
        files: List[UploadFile] = File(..., description="多个音频文件"),
        model_name: str = Query(DEFAULT_MODEL, description="HuggingFace模型仓库ID"),
        beam_size: int = Query(DEFAULT_BEAM_SIZE, description="Beam Size"),
        device: str = Query(DEFAULT_DEVICE, description="运行设备: cpu/cuda"),
        compute_type: str = Query(DEFAULT_COMPUTE_TYPE, description="计算精度"),
        language: str = Query(None, description="指定语言代码（如zh、en），可选"),
        max_concurrent: int = Query(DEFAULT_MAX_CONCURRENT, ge=MIN_CONCURRENT_LIMIT, le=MAX_CONCURRENT_LIMIT, description="最大并发处理数")
):

    """批量转录音频文件（并行处理）"""
    logging.info(f"开始转写音频文件，使用模型：{model_name}，运行设备：{device}，计算精度：{compute_type}，请耐心等待......")
    # 验证模型是否支持
    if model_name not in SUPPORTED_MODELS:
        return ApiResponse.error_response(f"不支持的模型。支持的模型: {', '.join(SUPPORTED_MODELS)}", 400)

    if not files:
        return ApiResponse.error_response("请至少上传一个文件", 400)

    # 先保存所有临时文件
    temp_files = []
    for file in files:
        suffix = "." + file.filename.split('.')[-1] if '.' in file.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            temp_files.append({
                "filename": file.filename,
                "path": tmp.name,
                "content_type": file.content_type
            })

    results = []
    try:
        # 验证所有文件的格式
        valid_files = []
        for file_info in temp_files:
            if file_info["content_type"] not in ALLOWED_AUDIO_TYPES:
                results.append({
                    "filename": file_info["filename"],
                    "transcript": None,
                    "error": "不支持的音频格式"
                })
            else:
                valid_files.append(file_info)

        if valid_files:
            # 预先加载模型（所有文件共享同一个模型实例）
            loop = asyncio.get_running_loop()
            model = await loop.run_in_executor(executor, get_model, model_name, device, compute_type)

            # 处理函数（用于线程池）
            def process_file(file_info):
                try:
                    result = transcribe_audio(model, file_info["path"], beam_size, language)
                    result["filename"] = file_info["filename"]
                    return result
                except Exception as e:
                    return {"filename": file_info["filename"], "transcript": None, "error": str(e)}

            # 使用新的线程池并行处理有效文件
            with ThreadPoolExecutor(max_workers=max_concurrent) as batch_executor:
                # 提交所有任务
                futures = [batch_executor.submit(process_file, f) for f in valid_files]

                # 收集结果
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append({"filename": "unknown", "transcript": None, "error": str(e)})

        response_data = {
            "total_files": len(files),
            "processed_files": len([r for r in results if "error" not in r]),
            "results": results
        }

        return ApiResponse.success_response(data=response_data)

    except Exception as e:
        return ApiResponse.error_response(f"批量转写失败: {str(e)}", 500)

    finally:
        # 清理所有临时文件
        for file_info in temp_files:
            if os.path.exists(file_info["path"]):
                os.unlink(file_info["path"])


@router.post("/transcribe-sliced")
async def transcribe_sliced(
        file: UploadFile = File(...),
        model_name: str = Query(DEFAULT_MODEL, description="HuggingFace模型仓库ID"),
        beam_size: int = Query(DEFAULT_BEAM_SIZE, description="Beam Size"),
        device: str = Query(DEFAULT_DEVICE, description="运行设备: cpu/cuda"),
        compute_type: str = Query(DEFAULT_COMPUTE_TYPE, description="计算精度"),
        language: str = Query(None, description="指定语言代码（如zh、en），可选"),
        max_concurrent: int = Query(None, description="最大并发处理数（可选，推荐让系统自动计算）"),
        consider_system_load: bool = Query(True, description="是否考虑系统当前负载"),
        slice_threshold: float = Query(AUDIO_SLICE_CONFIG["threshold"], description="静音检测阈值(dB)"),
        min_slice_length: int = Query(AUDIO_SLICE_CONFIG["min_slice_length"], description="最小切片长度(ms)"),
):
    """使用音频切片并行转录音频文件"""
    logging.info(f"开始转写音频文件，使用模型：{model_name}，运行设备：{device}，计算精度：{compute_type}，请耐心等待......")
    # 验证模型是否支持
    if model_name not in SUPPORTED_MODELS:
        return ApiResponse.error_response(f"不支持的模型。支持的模型: {', '.join(SUPPORTED_MODELS)}", 400)

    # 验证音频格式
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        return ApiResponse.error_response("不支持的音频格式", 400)

    # 保存原始文件到临时目录
    original_temp_path = None
    slice_infos = []

    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            contents = await file.read()
            tmp.write(contents)
            original_temp_path = tmp.name

        # 获取音频时长
        audio_duration = librosa.get_duration(filename=original_temp_path)
        logging.info(f"音频总时长: {audio_duration/60:.1f}分钟")

        # 使用音频切片器处理文件
        slice_infos = slice_audio_file(
            original_temp_path,
            threshold=slice_threshold,
            min_length=min_slice_length
        )
        logging.info(f"生成 {len(slice_infos)} 个音频切片")

        # 限制最大切片数量
        if len(slice_infos) > AUDIO_SLICE_CONFIG["max_total_slices"]:
            logging.warning(f"切片数量过多！！！ ({len(slice_infos)})，进行优化合并")
            slice_infos = merge_large_slices(slice_infos, AUDIO_SLICE_CONFIG["max_total_slices"])
        logging.info(f"生成 {len(slice_infos)} 个音频切片，平均时长: {audio_duration / len(slice_infos):.1f}秒")

        # 动态计算并发数（如果用户没有指定）
        if max_concurrent is None:
            max_concurrent = calculate_optimal_concurrency(len(slice_infos), audio_duration, consider_system_load)
            # 获取系统信息用于日志
            system_info = concurrency_optimizer.get_system_info()
            logging.info(f"系统信息: {system_info}")
            logging.info(f"自动计算最优并发数: {max_concurrent}")

        if not slice_infos:
            return ApiResponse.error_response("音频切片失败，未生成有效切片", 500)

        # 预先加载模型（所有切片共享同一个模型实例）
        loop = asyncio.get_running_loop()
        model = await loop.run_in_executor(executor, get_model, model_name, device, compute_type)

        # 并行处理所有切片
        results = []
        with ThreadPoolExecutor(max_workers=max_concurrent) as batch_executor:
            # 为每个切片创建处理任务
            futures = [
                batch_executor.submit(process_slice, model, s, beam_size, language)
                for s in slice_infos
            ]

            # 收集所有结果
            for future in as_completed(futures):
                try:
                    result = future.result()
                    slice_info = next(s for s in slice_infos if s["index"] == result.get("slice_index"))
                    # 校正时间戳（加上切片开始时间）
                    if "segments" in result:
                        for segment in result["segments"]:
                            segment["start"] += slice_info["start_time"]
                            segment["end"] += slice_info["start_time"]
                    result["slice_start_time"] = slice_info["start_time"]
                    results.append(result)
                except Exception as e:
                    slice_idx = slice_infos[len(results)]["index"] if len(results) < len(slice_infos) else "unknown"
                    results.append({
                        "slice_index": slice_idx,
                        "slice_start_time": 0,
                        "error": str(e),
                        "transcript": None
                    })

        # 按时间顺序排序结果
        results.sort(key=lambda x: x.get("slice_start_time", 0))

        # 聚合所有切片的结果
        final_result = aggregate_results(results)
        final_result["slice_count"] = len(slice_infos)
        final_result["processing_mode"] = "sliced_parallel"

        return ApiResponse.success_response(data=final_result)

    except Exception as e:
        return ApiResponse.error_response(f"处理失败: {str(e)}", 500)

    finally:
        # 清理临时文件
        if original_temp_path and os.path.exists(original_temp_path):
            os.unlink(original_temp_path)
        if slice_infos:
            cleanup_slices(slice_infos)