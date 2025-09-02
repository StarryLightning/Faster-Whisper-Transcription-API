# core/audio_slicer.py
import logging
import os
from typing import List

import librosa


def merge_large_slices(slice_infos: List[dict], max_slices: int) -> List[dict]:
    """
    合并过多的音频切片，保持合理的切片数量

    Args:
        slice_infos: 原始切片信息列表
        max_slices: 最大允许的切片数量

    Returns:
        合并后的切片信息列表
    """
    if len(slice_infos) <= max_slices:
        return slice_infos

    # 计算需要合并的批次数量
    merge_factor = len(slice_infos) // max_slices + 1
    merged_slices = []

    for i in range(0, len(slice_infos), merge_factor):
        batch = slice_infos[i:i + merge_factor]

        if len(batch) == 1:
            # 单个切片不需要合并
            merged_slices.append(batch[0])
        else:
            # 合并多个切片
            merged_slice = _merge_slice_batch(batch)
            merged_slices.append(merged_slice)

    logging.info(f"切片合并完成: {len(slice_infos)} -> {len(merged_slices)}")
    return merged_slices


def _merge_slice_batch(slice_batch: List[dict]) -> dict:
    """
    合并一个批次的切片文件

    Args:
        slice_batch: 要合并的切片批次

    Returns:
        合并后的切片信息
    """
    if not slice_batch:
        raise ValueError("切片批次不能为空")

    # 如果是单个切片，直接返回
    if len(slice_batch) == 1:
        return slice_batch[0]

    import numpy as np
    import soundfile as sf

    # 获取第一个切片的信息
    first_slice = slice_batch[0]
    merged_audio = None
    sample_rate = None

    # 合并所有音频数据
    for slice_info in slice_batch:
        try:
            audio, sr = librosa.load(slice_info['path'], sr=None, mono=False)
            if sample_rate is None:
                sample_rate = sr

            # 确保采样率一致
            if sr != sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=sample_rate)

            # 合并音频
            if merged_audio is None:
                merged_audio = audio
            else:
                if merged_audio.ndim == audio.ndim:
                    merged_audio = np.concatenate([merged_audio, audio], axis=merged_audio.ndim - 1)
                else:
                    # 处理声道数不匹配
                    if merged_audio.ndim == 1:
                        merged_audio = np.tile(merged_audio, (2, 1))
                    if audio.ndim == 1:
                        audio = np.tile(audio, (2, 1))
                    merged_audio = np.concatenate([merged_audio, audio], axis=1)

        except Exception as e:
            logging.error(f"加载切片失败 {slice_info['path']}: {e}")
            continue

    # 保存合并后的音频文件
    if merged_audio is not None:
        output_dir = os.path.dirname(first_slice['path'])
        merged_filename = f"merged_{first_slice['index']}_{slice_batch[-1]['index']}.wav"
        merged_path = os.path.join(output_dir, merged_filename)

        try:
            sf.write(merged_path, merged_audio.T if merged_audio.ndim > 1 else merged_audio, sample_rate)
        except Exception as e:
            logging.error(f"保存合并音频失败: {e}")
            return first_slice  # 失败时返回第一个切片

        # 计算合并后的总时长
        total_duration = sum(s.get('duration', 0) for s in slice_batch)

        return {
            'path': merged_path,
            'index': first_slice['index'],
            'duration': total_duration,
            'start_time': first_slice['start_time'],
            'is_merged': True,
            'merged_count': len(slice_batch),
            'original_indices': [s['index'] for s in slice_batch]
        }

    # 如果合并失败，返回第一个切片
    return first_slice


def cleanup_merged_slices(slice_infos: List[dict]):
    """
    清理合并的切片文件（包括原始切片和合并后的切片）
    """
    for slice_info in slice_infos:
        if os.path.exists(slice_info['path']):
            try:
                os.unlink(slice_info['path'])
            except Exception as e:
                logging.warning(f"清理文件失败 {slice_info['path']}: {e}")

        # 如果是合并的切片，也清理原始切片
        if slice_info.get('is_merged', False):
            original_indices = slice_info.get('original_indices', [])
            # 这里可以根据需要清理原始切片文件