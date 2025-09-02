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

    for result in slice_results:
        if "error" in result:
            # 记录错误但继续处理其他切片
            continue

        if "transcript" in result:
            full_text += result["transcript"] + " "

        if "segments" in result:
            all_segments.extend(result["segments"])

        # 使用第一个成功切片的语言检测结果
        if "language" in result and detected_language is None:
            detected_language = result["language"]
            language_probability = result.get("language_probability", 0)

    # 按时间戳排序所有分段
    all_segments.sort(key=lambda x: x["start"])

    return {
        "transcript": full_text.strip(),
        "language": detected_language,
        "language_probability": language_probability,
        "segments": all_segments,
        "total_segments": len(all_segments)
    }