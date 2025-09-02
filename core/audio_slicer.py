"""
音频切片模块 - 基于静音检测的长音频分割工具
"""

import numpy as np
import os
import tempfile
from typing import List, Optional
import librosa
import soundfile as sf
from config.settings import AUDIO_SLICE_CONFIG


# This function is obtained from librosa.
def get_rms(
        y: np.ndarray,
        *,
        frame_length: int = 2048,
        hop_length: int = 512,
        pad_mode: str = "constant",
) -> np.ndarray:
    """
    计算音频信号的RMS（均方根）能量
    """
    padding = (int(frame_length // 2), int(frame_length // 2))
    y = np.pad(y, padding, mode=pad_mode)

    axis = -1
    # put our new within-frame axis at the end for now
    out_strides = y.strides + tuple([y.strides[axis]])
    # Reduce the shape on the framing axis
    x_shape_trimmed = list(y.shape)
    x_shape_trimmed[axis] -= frame_length - 1
    out_shape = tuple(x_shape_trimmed) + tuple([frame_length])
    xw = np.lib.stride_tricks.as_strided(
        y, shape=out_shape, strides=out_strides
    )
    if axis < 0:
        target_axis = axis - 1
    else:
        target_axis = axis + 1
    xw = np.moveaxis(xw, -1, target_axis)
    # Downsample along the target axis
    slices = [slice(None)] * xw.ndim
    slices[axis] = slice(0, None, hop_length)
    x = xw[tuple(slices)]

    # Calculate power
    power = np.mean(np.abs(x) ** 2, axis=-2, keepdims=True)

    return np.sqrt(power)


class AudioSlicer:
    """
    音频切片器 - 基于静音检测自动分割长音频
    """

    def __init__(self,
                 sr: int,
                 threshold: float = -40.,
                 min_length: int = 5000,
                 min_interval: int = 300,
                 hop_size: int = 20,
                 max_sil_kept: int = 5000):
        """
        初始化音频切片器

        Args:
            sr: 采样率
            threshold: 静音阈值(dB)
            min_length: 最小切片长度(ms)
            min_interval: 最小静音间隔(ms)
            hop_size: 跳数大小(ms)
            max_sil_kept: 最大保留静音长度(ms)
        """
        if not min_length >= min_interval >= hop_size:
            raise ValueError('min_length >= min_interval >= hop_size')
        if not max_sil_kept >= hop_size:
            raise ValueError('max_sil_kept >= hop_size')

        self.sr = sr
        self.threshold = 10 ** (threshold / 20.)
        self.hop_size = round(sr * hop_size / 1000)
        self.win_size = min(round(min_interval), 4 * self.hop_size)
        self.min_length = round(sr * min_length / 1000 / self.hop_size)
        self.min_interval = round(min_interval / self.hop_size)
        self.max_sil_kept = round(sr * max_sil_kept / 1000 / self.hop_size)

    def _apply_slice(self, waveform: np.ndarray, begin: int, end: int) -> np.ndarray:
        """应用切片到波形数据"""
        if len(waveform.shape) > 1:
            return waveform[:, begin * self.hop_size: min(waveform.shape[1], end * self.hop_size)]
        else:
            return waveform[begin * self.hop_size: min(waveform.shape[0], end * self.hop_size)]

    def slice(self, waveform: np.ndarray) -> List[np.ndarray]:
        """
        对音频波形进行切片

        Args:
            waveform: 音频波形数据

        Returns:
            切片后的音频片段列表
        """
        if len(waveform.shape) > 1:
            samples = waveform.mean(axis=0)
        else:
            samples = waveform

        if (samples.shape[0] + self.hop_size - 1) // self.hop_size <= self.min_length:
            return [waveform]

        rms_list = get_rms(y=samples, frame_length=self.win_size, hop_length=self.hop_size).squeeze(0)
        sil_tags = []
        silence_start = None
        clip_start = 0

        for i, rms in enumerate(rms_list):
            # Keep looping while frame is silent.
            if rms < self.threshold:
                # Record start of silent frames.
                if silence_start is None:
                    silence_start = i
                continue
            # Keep looping while frame is not silent and silence start has not been recorded.
            if silence_start is None:
                continue
            # Clear recorded silence start if interval is not enough or clip is too short
            is_leading_silence = silence_start == 0 and i > self.max_sil_kept
            need_slice_middle = i - silence_start >= self.min_interval and i - clip_start >= self.min_length
            if not is_leading_silence and not need_slice_middle:
                silence_start = None
                continue
            # Need slicing. Record the range of silent frames to be removed.
            if i - silence_start <= self.max_sil_kept:
                pos = rms_list[silence_start: i + 1].argmin() + silence_start
                if silence_start == 0:
                    sil_tags.append((0, pos))
                else:
                    sil_tags.append((pos, pos))
                clip_start = pos
            elif i - silence_start <= self.max_sil_kept * 2:
                pos = rms_list[i - self.max_sil_kept: silence_start + self.max_sil_kept + 1].argmin()
                pos += i - self.max_sil_kept
                pos_l = rms_list[silence_start: silence_start + self.max_sil_kept + 1].argmin() + silence_start
                pos_r = rms_list[i - self.max_sil_kept: i + 1].argmin() + i - self.max_sil_kept
                if silence_start == 0:
                    sil_tags.append((0, pos_r))
                    clip_start = pos_r
                else:
                    sil_tags.append((min(pos_l, pos), max(pos_r, pos)))
                    clip_start = max(pos_r, pos)
            else:
                pos_l = rms_list[silence_start: silence_start + self.max_sil_kept + 1].argmin() + silence_start
                pos_r = rms_list[i - self.max_sil_kept: i + 1].argmin() + i - self.max_sil_kept
                if silence_start == 0:
                    sil_tags.append((0, pos_r))
                else:
                    sil_tags.append((pos_l, pos_r))
                clip_start = pos_r
            silence_start = None

        # Deal with trailing silence.
        total_frames = rms_list.shape[0]
        if silence_start is not None and total_frames - silence_start >= self.min_interval:
            silence_end = min(total_frames, silence_start + self.max_sil_kept)
            pos = rms_list[silence_start: silence_end + 1].argmin() + silence_start
            sil_tags.append((pos, total_frames + 1))

        # Apply and return slices.
        if len(sil_tags) == 0:
            return [waveform]
        else:
            chunks = []
            if sil_tags[0][0] > 0:
                chunks.append(self._apply_slice(waveform, 0, sil_tags[0][0]))
            for i in range(len(sil_tags) - 1):
                chunks.append(self._apply_slice(waveform, sil_tags[i][1], sil_tags[i + 1][0]))
            if sil_tags[-1][1] < total_frames:
                chunks.append(self._apply_slice(waveform, sil_tags[-1][1], total_frames))
            return chunks


def slice_audio_file(input_path: str,
                     output_dir: Optional[str] = None,
                     threshold: Optional[float] = None,
                     min_length: Optional[int] = None,
                     min_interval: Optional[int] = None,
                     hop_size: Optional[int] = None,
                     max_sil_kept: Optional[int] = None) -> List[dict]:
    """
    使用智能配置切片音频文件
    """
    # 使用配置默认值或传入参数
    threshold = threshold or AUDIO_SLICE_CONFIG["threshold"]
    min_length = min_length or AUDIO_SLICE_CONFIG["min_slice_length"]
    min_interval = min_interval or AUDIO_SLICE_CONFIG["min_interval"]
    hop_size = hop_size or AUDIO_SLICE_CONFIG["hop_size"]
    max_sil_kept = max_sil_kept or AUDIO_SLICE_CONFIG["max_sil_kept"]

    """
    切片音频文件并保存结果

    Args:
        input_path: 输入音频文件路径
        output_dir: 输出目录，如果为None则使用临时目录
        threshold: 静音阈值(dB)
        min_length: 最小切片长度(ms)
        min_interval: 最小静音间隔(ms)
        hop_size: 跳数大小(ms)
        max_sil_kept: 最大保留静音长度(ms)

    Returns:
        切片信息列表，包含文件路径、持续时间等信息
    """

    # 创建输出目录
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)

    # 加载音频文件
    audio, sr = librosa.load(input_path, sr=None, mono=False)

    # 创建切片器
    slicer = AudioSlicer(
        sr=sr,
        threshold=threshold,
        min_length=min_length,
        min_interval=min_interval,
        hop_size=hop_size,
        max_sil_kept=max_sil_kept
    )

    # 执行切片
    chunks = slicer.slice(audio)

    # 保存切片文件并收集信息
    slice_infos = []
    base_name = os.path.basename(input_path).rsplit('.', maxsplit=1)[0]
    total_duration = 0.0

    for i, chunk in enumerate(chunks):
        # 计算持续时间
        duration = len(chunk) / sr if len(chunk.shape) == 1 else len(chunk[0]) / sr

        # 保存文件
        output_path = os.path.join(output_dir, f"{base_name}_slice_{i:04d}.wav")
        if len(chunk.shape) > 1:
            chunk = chunk.T  # 转置多声道音频
        sf.write(output_path, chunk, sr)

        slice_infos.append({
            "path": output_path,
            "index": i,
            "duration": duration,
            "start_time": total_duration
        })

        total_duration += duration

    return slice_infos


def cleanup_slices(slice_infos: List[dict]):
    """
    清理切片文件

    Args:
        slice_infos: 切片信息列表
    """
    for info in slice_infos:
        if os.path.exists(info["path"]):
            os.unlink(info["path"])

    # 尝试删除空目录
    if slice_infos:
        output_dir = os.path.dirname(slice_infos[0]["path"])
        if os.path.exists(output_dir) and not os.listdir(output_dir):
            os.rmdir(output_dir)