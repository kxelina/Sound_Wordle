"""Deterministic, gain-invariant audio comparison; no target patch access.

Scores are engineering distances, not calibrated perceptual percentages.
The shared timeline is intentional: onset/release/echo errors must remain audible.
"""

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf

from .clue_features import CONTEXT_CLUES, DiagnosticContext, contextual_diagnosis


ALGORITHM_VERSION = "audio-match-v1"
MAX_SECONDS = 30


@dataclass(frozen=True)
class MatchConfig:
    focus: Literal["combined", "spectrum", "envelope"] = "combined"
    pass_score: float = 90.
    component_floor: float = 85.
    tail_floor: float = 85.

    def __post_init__(self):
        if self.focus not in ("combined", "spectrum", "envelope"):
            raise ValueError("Unknown scoring focus")
        for value in (self.pass_score, self.component_floor, self.tail_floor):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("Score thresholds must be finite numbers from 0 to 100")


@dataclass(frozen=True)
class MatchResult:
    total: float
    spectrum: float
    envelope: float
    tail: float
    passed: bool
    diagnostics: tuple[str, ...]
    measurements: dict[str, float]
    config: MatchConfig
    version: str = ALGORITHM_VERSION

    def to_dict(self):
        return asdict(self)


CLUES = {
    "close": ("No large measured difference. Listen again before making small changes.", "未測到明顯差異；細調前可再試聽比較。"),
    "duller": ("Your sound has less high-frequency energy. Try stronger upper harmonics or a higher low-pass cutoff.", "目前聲音的高頻較少，可嘗試增加高次諧波或提高低通截止頻率。"),
    "brighter": ("Your sound has more high-frequency energy. Try weaker upper harmonics or a lower low-pass cutoff.", "目前聲音的高頻較多，可嘗試減少高次諧波或降低低通截止頻率。"),
    "spectrum": ("The spectral balance differs. Compare the harmonic mix; brightness alone may not explain it.", "頻譜分布有差異；請比較諧波比例，差異未必只在明亮程度。"),
    "slower_attack": ("Your first attack rises more slowly. Try a shorter Attack.", "目前聲音的首次起音較慢，可嘗試縮短 Attack。"),
    "faster_attack": ("Your first attack rises faster. Try a longer Attack.", "目前聲音的首次起音較快，可嘗試延長 Attack。"),
    "longer_tail": ("Your sound continues after the target ends. Check Release, Delay and Reverb.", "目標結束後，目前聲音仍持續；請檢查 Release、回聲及混響。"),
    "shorter_tail": ("Your sound ends earlier. Check Release and any missing effect tail.", "目前聲音較早結束；請檢查 Release 及音效尾音是否不足。"),
    "envelope": ("The volume shape over time differs. Check ADSR and repeated or lingering sound.", "音量隨時間的形狀有差異；請檢查 ADSR、重複聲及殘響。"),
}
CLUES.update(CONTEXT_CLUES)


def diagnose(result: MatchResult, language="en") -> tuple[str, ...]:
    """Localize measured clue codes; never infer a unique hidden knob value."""
    if language not in ("en", "zh-Hant"):
        raise ValueError("Unsupported clue language")
    return tuple(CLUES[code][language == "zh-Hant"] for code in result.diagnostics)


def _audio(value, rate):
    data = np.asarray(value, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    if data.ndim != 2 or data.shape[1] not in (1, 2):
        raise ValueError("Audio must be mono or stereo (samples, channels)")
    if not round(.05 * rate) <= len(data) <= MAX_SECONDS * rate:
        raise ValueError("Comparison audio must be between 0.05 and 30 seconds")
    if not np.isfinite(data).all():
        raise ValueError("Audio contains non-finite samples")
    peak = float(np.max(np.abs(data)))
    if peak <= 1e-12:
        raise ValueError("Cannot score silence; add a harmonic and preview again")
    if data.shape[1] == 2 and np.array_equal(data[:, 0], data[:, 1]):
        data = data[:, :1]  # Identical stereo needs only one FFT, with identical energy.
    # Normalize before squaring, also avoiding overflow for unusually large floats.
    return data / peak


def _rms(data, width, hop):
    power = np.mean(data * data, axis=1)
    padded = np.pad(power, (width // 2, width - width // 2))
    integral = np.concatenate(([0.], np.cumsum(padded)))
    starts = np.arange(0, len(data), hop)
    return np.sqrt(np.maximum(0., (integral[starts + width] - integral[starts]) / width))


def _spectra(data):
    size, hop = 2048, 256
    padded = np.pad(data, ((size // 2, size // 2), (0, 0)))
    frames = np.lib.stride_tricks.sliding_window_view(padded, size, axis=0)[::hop][:math.ceil(len(data) / hop)]
    window = np.hanning(size)
    parts = []
    # Bound working FFT allocations; never create a 30 s x 2048 x stereo copy.
    for offset in range(0, len(frames), 128):
        fft = np.fft.rfft(frames[offset:offset + 128] * window, axis=-1)
        parts.append(np.sqrt(np.mean(np.abs(fft) ** 2, axis=1)).astype(np.float32))
    return np.concatenate(parts)


def _balanced_mean(values, times, mask):
    """Balance the overall shape with 200 ms local errors, without time warping."""
    selected = values[mask]
    if not len(selected):
        return 0.
    blocks = (times[mask] / .2).astype(int)
    totals = np.bincount(blocks, weights=selected)
    counts = np.bincount(blocks)
    local = totals[counts > 0] / counts[counts > 0]
    return float(.6 * selected.mean() + .4 * np.quantile(local, .9))


def _attack(envelope, hop_seconds):
    audible = np.flatnonzero(envelope > .01)
    start = int(audible[0])
    region = envelope[start:start + max(1, round(.45 / hop_seconds))]
    peak_index = int(np.argmax(region))
    rising = region[:peak_index + 1]
    peak = float(rising[-1])
    low = np.flatnonzero(rising >= peak * .1)[0]
    high = np.flatnonzero(rising >= peak * .9)[0]
    return float((high - low) * hop_seconds)


def compare(target_audio, player_audio, sample_rate=44100, *, config=None, context=None) -> MatchResult:
    """Compare aligned raw audio. Different durations are zero-padded, never stretched.

    Same note timeline is required for restoration. Any timing/pitch differences
    count as differences; no score can identify the uniquely correct synth patch.
    """
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
        raise ValueError("Sample rate must be an integer from 8000 to 192000 Hz")
    config = config if config is not None else MatchConfig()
    if not isinstance(config, MatchConfig):
        raise TypeError("config must be MatchConfig")
    if context is not None and not isinstance(context, DiagnosticContext):
        raise TypeError("context must be DiagnosticContext")
    target, player = _audio(target_audio, sample_rate), _audio(player_audio, sample_rate)
    length = max(len(target), len(player))
    target, player = (np.pad(data, ((0, length - len(data)), (0, 0))) for data in (target, player))
    hop = round(sample_rate * .005)
    width = round(sample_rate * .02)
    te, pe = (_rms(data, width, hop) for data in (target, player))
    te, pe = te / te.max(), pe / pe.max()
    times = np.arange(len(te)) * hop / sample_rate
    active = (te > .01) | (pe > .01)
    # Linear amplitude preserves the main body; log amplitude exposes quiet tails.
    log_t, log_p = (np.log10(np.maximum(curve, .01)) / 2 for curve in (te, pe))
    point_error = .7 * np.abs(te - pe) + .3 * np.abs(log_t - log_p)
    envelope_error = min(1., 2 * _balanced_mean(point_error, times, active))

    ts, ps = _spectra(target), _spectra(player)
    # Compare spectral shape only while both sounds are active. Missing sound is
    # measured by the envelope and tail checks, rather than labelled a new timbre.
    strengths = [np.sqrt(np.sum(spectrum ** 2, axis=1)) for spectrum in (ts, ps)]
    shared = (strengths[0] > strengths[0].max() * .01) & (strengths[1] > strengths[1].max() * .01)
    centroids = []
    distributions = []
    frequencies = np.fft.rfftfreq(2048, 1 / sample_rate)
    for spectrum in (ts, ps):
        spectrum = spectrum.copy()
        spectrum[spectrum < spectrum.max(axis=1, keepdims=True) * .001] = 0
        spectrum /= np.maximum(spectrum.sum(axis=1, keepdims=True), 1e-30)
        distributions.append(spectrum)
        # Reduce frames first: a BLAS matrix/vector call can start many worker
        # threads for this tiny reduction and cost more than the FFT itself.
        centroids.append(float(np.sum(np.mean(spectrum[shared], axis=0, dtype=np.float64) * frequencies)) if shared.any() else 0.)
    distances = np.sqrt(np.clip(.5 * np.sum((np.sqrt(distributions[0]) - np.sqrt(distributions[1])) ** 2, axis=1), 0, 1))
    spectrum_error = min(1., 1.25 * _balanced_mean(distances, np.arange(len(ts)) * 256 / sample_rate, shared)) if shared.any() else 1.

    target_end = float(times[np.flatnonzero(te > .01)[-1]])
    player_end = float(times[np.flatnonzero(pe > .01)[-1]])
    # Late energy relative to the final second, so long phrases cannot hide an
    # extra echo behind the energy of all their earlier notes. A 20 ms guard
    # tolerates the finite RMS analysis window at the reference boundary.
    late = times > target_end + .02
    final_region = times >= max(0., target_end - 1.)
    late_fraction = float(np.sum(pe[late] ** 2) / max(np.sum(pe[final_region] ** 2), 1e-30))
    # A reverberant reference can itself contain energy below the audible-end
    # threshold. Keep the established score, but diagnose only *extra* late
    # energy relative to that reference; a self-match must not get a tail clue.
    target_late_fraction = float(np.sum(te[late] ** 2) / max(np.sum(te[final_region] ** 2), 1e-30))
    extra_tail_error = math.sqrt(max(0., late_fraction - target_late_fraction))
    tail_error = min(1., math.sqrt(late_fraction))
    spectrum_score, envelope_score, tail_score = (100 * (1 - error) for error in (spectrum_error, envelope_error, tail_error))
    total = {"combined": (spectrum_score + envelope_score) / 2,
             "spectrum": spectrum_score, "envelope": envelope_score}[config.focus]
    passed = total >= config.pass_score
    if config.focus == "combined":
        passed = passed and min(spectrum_score, envelope_score) >= config.component_floor
    if config.focus != "spectrum":
        passed = passed and tail_score >= config.tail_floor

    attack_delta = _attack(pe, hop / sample_rate) - _attack(te, hop / sample_rate)
    centroid_ratio = centroids[1] / max(centroids[0], 1e-30)
    candidates = []
    if config.focus != "envelope" and spectrum_error > .05:
        candidates.append((spectrum_error, "duller" if centroid_ratio < .90 else "brighter" if centroid_ratio > 1.10 else "spectrum"))
    if config.focus != "spectrum":
        if extra_tail_error > .03 or (player_end - target_end > .06 and envelope_error > .02):
            candidates.append((max(tail_error, envelope_error), "longer_tail"))
        elif target_end - player_end > .06 and envelope_error > .02:
            candidates.append((envelope_error, "shorter_tail"))
        if abs(attack_delta) > .035 and envelope_error > .02:
            candidates.append((envelope_error, "slower_attack" if attack_delta > 0 else "faster_attack"))
        if envelope_error > .02 and not any(code in ("slower_attack", "faster_attack", "longer_tail", "shorter_tail") for _, code in candidates):
            candidates.append((envelope_error, "envelope"))
    clues = tuple(code for _, code in sorted(candidates, key=lambda item: -item[0])) or ("close",)
    measurements = {"spectrum_error": spectrum_error, "envelope_error": envelope_error,
                    "late_energy_fraction": late_fraction, "target_late_energy_fraction": target_late_fraction,
                    "target_end_seconds": target_end,
                    "player_end_seconds": player_end, "attack_delta_seconds": attack_delta,
                    "target_centroid_hz": centroids[0], "player_centroid_hz": centroids[1]}
    specific, evidence = contextual_diagnosis(context, target, player, sample_rate, (te, pe), times, (ts, ps), measurements)
    measurements.update(evidence)
    if specific:
        clues = specific + tuple(code for code in clues if code not in specific and code != "close")
    return MatchResult(float(total), spectrum_score, envelope_score, tail_score, bool(passed), clues, measurements, config)


def compare_files(target: str | Path, player: str | Path, *, config=None, context=None):
    # Check headers before loading; reject mismatched rates instead of silently
    # resampling or allocating an arbitrarily long file on the UI worker.
    infos = [sf.info(path) for path in (target, player)]
    if infos[0].samplerate != infos[1].samplerate:
        raise ValueError("Comparison WAV files must use the same sample rate")
    for info in infos:
        if not .05 <= info.duration <= MAX_SECONDS or info.channels not in (1, 2):
            raise ValueError("Comparison requires 0.05–30 second mono/stereo audio")
    arrays = [sf.read(path, always_2d=True)[0] for path in (target, player)]
    return compare(*arrays, infos[0].samplerate, config=config, context=context)
