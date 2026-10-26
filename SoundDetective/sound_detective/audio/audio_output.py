"""播放电平准备；不修改生成音频，也不把输出音量写进 SynthPatch。"""

import numpy as np
from .models import bounded


def prepare_playback(audio: np.ndarray, volume: float = 0.5,
                     target_rms: float = 0.1, peak_limit: float = 0.9) -> np.ndarray:
    """近似 RMS 匹配并留峰值余量。volume 在匹配后应用。"""
    bounded("volume", volume, 0, 1)
    bounded("target_rms", target_rms, 0.001, 0.25)
    bounded("peak_limit", peak_limit, 0.1, 0.95)
    source = np.asarray(audio, dtype=np.float64)
    if source.ndim not in (1, 2) or source.size == 0 or not np.isfinite(source).all():
        raise ValueError("Expected nonempty finite mono/stereo audio")
    if source.ndim == 2 and source.shape[1] not in (1, 2):
        raise ValueError("Only mono/stereo audio is supported")
    magnitude = np.max(np.abs(source), axis=1) if source.ndim == 2 else np.abs(source)
    peak = float(magnitude.max())
    if peak < 1e-10:
        return np.zeros_like(source, dtype=np.float32)
    active = magnitude > peak * 0.01
    rms = float(np.sqrt(np.mean(source[active] ** 2)))
    gain = min(target_rms / max(rms, 1e-12), peak_limit / peak)
    return (source * gain * volume).astype(np.float32)
