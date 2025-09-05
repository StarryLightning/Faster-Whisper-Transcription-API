# core/processing_strategy.py

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from config.settings import ALLOWED_AUDIO_TYPES, AUDIO_SLICE_CONFIG, CONCURRENCY_CONFIG
from core.audio_slicer import slice_audio_file, cleanup_slices
from core.slice_tools.concurrency_optimizer import calculate_optimal_concurrency, concurrency_optimizer
from core.slice_tools.merge_slice import merge_large_slices
from core.slice_tools.process_slice import process_slice, aggregate_results
from core.transcriber import transcribe_audio

# 配置日志
logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

async def determine_processing_strategy(file_infos: List[dict], auto_slice: bool) -> str:
    # 确定最佳处理策略
    if len(file_infos) == 1:
        # 单个文件，根据时长决定是否切片
        file_info = file_infos[0]
        if auto_slice and file_info["requires_slicing"]:
            return "slice_only"
        else:
            return "batch_only"

    else:
        # 多个文件，检查是否有需要切片的音频
        has_long_audio = any(info["requires_slicing"] for info in file_infos)
        if has_long_audio and auto_slice:
            return "mixed"
        else:
            return "batch_only"


async def process_batch_strategy(file_infos, model, beam_size, language, max_concurrent):
    # 批量处理
    valid_files = [info for info in file_infos if info ["content_type"] in ALLOWED_AUDIO_TYPES]

    if not valid_files:
        return {
            "total_files": len(file_infos),
            "processed_files": 0,
            "strategy": "batch_parallel",
            "results": [],
            "error": "Invalid Audio Files"
        }

    def process_file(file_info):
        try:
            result = transcribe_audio(model, file_info["path"], beam_size, language)
            result["filename"] = file_info["filename"]
            result["duration"] = file_info["duration"]
            return result
        except Exception as e:
            return {"filename": file_info["filename"], "transcript": None, "error": str(e), "duration": file_info["duration"]}

    results = []
    effective_concurrent = max_concurrent or CONCURRENCY_CONFIG["default_max_concurrent"]
    effective_concurrent = min(effective_concurrent, len(valid_files))

    with ThreadPoolExecutor(max_workers = effective_concurrent) as batch_executor:
        futures = [batch_executor.submit(process_file, f) for f in valid_files]
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)

            except Exception as e:
                results.append({
                    "filename": "unknown",
                    "transcript": None,
                    "error": str(e),
                    "duration": 0
                })

    data = {
        "total_files": len(file_infos),
        "processed_files": len(results),
        "strategy": "batch_parallel",
        "results": results
    }
    return data


async def process_slice_strategy(file_info, model, beam_size,
                                 language, max_concurrent, consider_system_load):
    # 切片处理
    slice_infos = []
    try:
        slice_infos = slice_audio_file(
            file_info["path"],
            threshold=AUDIO_SLICE_CONFIG["threshold"],
            min_length=AUDIO_SLICE_CONFIG["min_slice_length"]
        )
        logger.info(f"生成 {len(slice_infos)} 个音频切片")

        if len(slice_infos) > AUDIO_SLICE_CONFIG["max_total_slices"]:
            logger.warning(f"切片数量过多！！！ ({len(slice_infos)})，进行优化合并")
            slice_infos = merge_large_slices(slice_infos, AUDIO_SLICE_CONFIG["max_total_slices"])

        # 动态计算并发数（如果用户没有指定）
        if max_concurrent is None:
            max_concurrent = calculate_optimal_concurrency(len(slice_infos), file_info["duration"], consider_system_load)
            # 获取系统信息用于日志
            system_info = concurrency_optimizer.get_system_info()
            logger.info(f"系统信息: {system_info}")
            logger.info(f"自动计算最优并发数: {max_concurrent}")
        else:
            # ✅ 用户指定了，就用用户的，但不超过切片数
            max_concurrent = min(max_concurrent, len(slice_infos))  # ← 新增：防止线程数 > 任务数

        # 加载模型处理切片

        results = []
        with ThreadPoolExecutor(max_workers = max_concurrent) as batch_executor:
            futures = [
                batch_executor.submit(process_slice, model, s, beam_size, language)
                for s in slice_infos
            ]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    slice_info = next(s for s in slice_infos if s["index"] == result.get("slice_index"))

                    if "segments" in result:
                        for segment in result["segments"]:
                            segment["start"] += slice_info["start_time"]
                            segment["end"] += slice_info["start_time"]
                    result["slice_start_time"] = slice_info["start_time"]
                    results.append(result)

                except Exception as e:
                    results.append({
                        "slice_index": "unknown",
                        "error": str(e),
                        "transcript": None
                    })

        # 聚合结果
        results.sort(key=lambda x: x.get("slice_start_time", 0))
        final_result = aggregate_results(results)
        final_result.update({
            "filename": file_info["filename"],
            "slice_count": len(slice_infos),
            "processing_mode": "sliced_parallel",
            "original_duration": file_info["duration"]
        })

        data = {
            "results" : [final_result]
        }
        return data

    except Exception as e:
        return {
            "results": [{
                "filename": file_info["filename"],
                "transcript": None,
                "error": f"切片处理失败: {str(e)}",
                "slice_count": 0,
                "processing_mode": "sliced_parallel",
                "original_duration": file_info["duration"]
            }]
        }
    finally:
        if slice_infos:
            cleanup_slices(slice_infos)


async def process_mixed_strategy(file_infos, model, beam_size,
                                  language, max_concurrent, consider_system_load):
    # 混合处理
    # 分离长短音频
    short_audio = [info for info in file_infos if not info["requires_slicing"]]
    long_audio = [info for info in file_infos if info["requires_slicing"]]

    results = []
    # 并行处理短音频
    if short_audio:
        # ✅ 传入 max_concurrent 控制短音频文件并发
        short_results = await process_batch_strategy(short_audio, model, beam_size, language, max_concurrent)
        if isinstance(short_results, dict) and "results" in short_results:
            results.extend(short_results["results"])

    # 串行处理长音频（避免资源竞争）
    for long_file in long_audio:
        # ✅ 传入 max_concurrent 控制该长音频的切片并发
        long_result = await process_slice_strategy(long_file, model, beam_size, language, max_concurrent, consider_system_load)
        if isinstance(long_result, dict) and "results" in long_result and len(long_result["results"]) > 0:
            results.append(long_result["results"][0])

    data = {
        "total_files": len(file_infos),
        "processed_files": len(results),
        "strategy": "mixed_optimized",
        "results": results
    }
    return data