import logging
from typing import List

from core.transcriber import transcribe_audio


def process_slice(model, slice_info, beam_size, language):
    """处理单个音频切片"""
    result = transcribe_audio(model, slice_info["path"], beam_size, language)
    result["slice_index"] = slice_info["index"]
    return result


def aggregate_results(slice_results: List[dict]) -> dict:
    """聚合所有切片的结果"""
    full_text = ""
    all_segments = []
    detected_language = None
    language_probability = 0
    total_slices = len(slice_results)
    failed_slices = 0

    for result in slice_results:
        if "error" in result:
            logging.warning(
                f"切片处理失败 [索引: {result.get('slice_index', 'N/A')}]: {result['error']}"
            )
            failed_slices += 1
            continue
        if "transcript" in result:
            full_text += result["transcript"] + " "
        if "segments" in result:
            all_segments.extend(result["segments"])
        if "language" in result and detected_language is None:
            detected_language = result["language"]
            language_probability = result.get("language_probability", 0)

    all_segments.sort(key=lambda x: x["start"])

    result_data = {
        "transcript": full_text.strip(),
        "language": detected_language,
        "language_probability": language_probability,
        "segments": all_segments,
        "total_segments": len(all_segments),
        "total_slices": total_slices,
        "successful_slices": total_slices - failed_slices,
        "failed_slices": failed_slices
    }

    if failed_slices > 0:
        result_data["warning"] = f"有 {failed_slices}/{total_slices} 个切片处理失败，结果可能不完整。"

    return result_data