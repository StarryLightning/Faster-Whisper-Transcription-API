# core/transcriber.py
import logging

from faster_whisper import WhisperModel

from core.MyThreadPool import transcribe_semaphore

logger = logging.getLogger(__name__)
def transcribe_audio(model: WhisperModel, file_path: str, beam_size: int, language: str = None):
    """音频转录实现"""
    transcribe_semaphore.acquire()
    logger.info(f"开始转录：{file_path}")
    try:
        # 设置转录参数
        transcribe_kwargs = {"beam_size": beam_size}
        if language:
            transcribe_kwargs["language"] = language

        segments, info = model.transcribe(file_path, **transcribe_kwargs)
        segments = list(segments)
        transcript = "".join(segment.text for segment in segments)

        return {
            "transcript": transcript,
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in segments
            ]
        }
    except Exception as e:
        logger.error(f"转录失败 {file_path}: {e}")
        return {"error": str(e)}
    finally:
        transcribe_semaphore.release()
        logger.info(f"完成转录: {file_path}")