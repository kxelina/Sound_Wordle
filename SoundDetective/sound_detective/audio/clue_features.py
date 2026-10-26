"""Measured case-specific clues using public note timing, never synth answers."""

from dataclasses import dataclass
import numpy as np

from .sequence import NoteSequence


@dataclass(frozen=True)
class DiagnosticContext:
    profile: str
    sequence: NoteSequence
    editable: tuple[str, ...] = ()

    def __post_init__(self):
        if self.profile not in ("adsr", "harmonics", "filter", "delay", "reverb", "combined") or not isinstance(self.sequence, NoteSequence) or not self.sequence.events:
            raise ValueError("Invalid diagnostic context")
        object.__setattr__(self, "editable", tuple(self.editable))


CONTEXT_CLUES = {
    "sustain_high": ("The held part is relatively louder. Try lowering Sustain.", "持續部分的相對音量較高，可嘗試降低 Sustain。"),
    "sustain_low": ("The held part is relatively quieter. Try increasing Sustain.", "持續部分的相對音量較低，可嘗試提高 Sustain。"),
    "decay_fast": ("The sound reaches its held level sooner. Try a longer Decay.", "聲音較快到達持續音量，可嘗試延長 Decay。"),
    "decay_slow": ("The sound takes longer to reach its held level. Try a shorter Decay.", "聲音較慢到達持續音量，可嘗試縮短 Decay。"),
    "echo_fast": ("The repeats are closer together. Try a longer Delay interval.", "重複聲的間隔較短，可嘗試延長回聲間隔。"),
    "echo_slow": ("The repeats are farther apart. Try a shorter Delay interval.", "重複聲的間隔較長，可嘗試縮短回聲間隔。"),
    "echo_missing": ("The reference's repeat pattern is not clearly present. Check Delay enable and wet mix.", "尚未清楚呈現參照的重複聲圖案，請檢查回聲開關與濕聲比例。"),
    "echo_weak": ("The repeats carry less relative energy. Check Delay wet mix and decay.", "重複聲的相對能量較少，請檢查回聲濕聲比例與衰減時間。"),
    "echo_strong": ("The repeats carry more relative energy. Check Delay wet mix and decay.", "重複聲的相對能量較多，請檢查回聲濕聲比例與衰減時間。"),
    "room_weak": ("The reverberant tail carries less relative energy. Check wet mix and room size.", "殘響尾音的相對能量較少，請檢查混響濕聲比例與空間大小。"),
    "room_strong": ("The reverberant tail carries more relative energy. Check wet mix and room size.", "殘響尾音的相對能量較多，請檢查混響濕聲比例與空間大小。"),
    "tail_bright": ("The reverberant tail is brighter. Try more Damping.", "殘響尾音較明亮，可嘗試增加阻尼。"),
    "tail_dark": ("The reverberant tail is darker. Try less Damping.", "殘響尾音較暗，可嘗試減少阻尼。"),
    "filter_shape": ("The spectral shape differs. Compare filter type, cutoff and resonance.", "頻譜形狀有差異，請比較濾波類型、截止頻率與共振。"),
    "filter_missing": ("Filter is off, while this case uses filtering. Enable it and compare the spectral shape before changing harmonics.", "Filter 目前關閉，但本案參照包含濾波。先開啟並比較頻譜形狀，再細調諧波。"),
    "filter_extra": ("Your Filter is active, while this case's reference is unfiltered. Try bypassing it first.", "目前啟用了 Filter，但本案參照沒有濾波；可先關閉再比較。"),
    "filter_family": ("The filter type differs from this case's reference. Compare low-pass and high-pass before compensating with harmonics.", "濾波類型與本案參照不同；先比較低通與高通，避免用諧波補償濾波差異。"),
    "delay_missing": ("Delay is off, while this case includes repeats. Enable Delay before trying to recreate the repeats with ADSR.", "Delay 目前關閉，但本案參照包含回聲。先開啟 Delay，無需用 ADSR 模仿重複聲。"),
    "delay_dry": ("Delay is enabled but its wet mix is zero. Raise Dry/Wet to hear the repeats, then compare spacing and decay.", "Delay 已開啟，但濕聲比例為零；先提高 Dry/Wet，聽到回聲後再比較間隔與衰減。"),
    "delay_extra": ("Your Delay is active, while this case's reference has no Delay. Try bypassing it first.", "目前啟用了 Delay，但本案參照沒有回聲；可先關閉再比較。"),
    "reverb_missing": ("Reverb is off, while this case includes a room tail. Enable Reverb before lengthening Release to fill that space.", "Reverb 目前關閉，但本案參照包含空間殘響。先開啟 Reverb，避免只拉長 Release 補尾音。"),
    "reverb_dry": ("Reverb is enabled but its wet mix is zero. Raise Dry/Wet, then compare room size and damping.", "Reverb 已開啟，但濕聲比例為零；先提高 Dry/Wet，再比較空間大小與阻尼。"),
    "reverb_extra": ("Your Reverb is active, while this case's reference has no Reverb. Try bypassing it first.", "目前啟用了 Reverb，但本案參照沒有混響；可先關閉再比較。"),
    "effects_tail_short": ("The late effect tail is weaker or missing, beyond the longest dry Release. Compare Delay/Reverb and the dry sound feeding them; this does not isolate an ADSR error.", "後段音效尾音不足或缺失，已超出最長乾聲 Release 的時段。請分別比較 Delay／Reverb 及送入音效的乾聲，不能直接斷定 ADSR 有錯。"),
    "effects_tail_long": ("The late effect tail carries more energy. Check Delay/Reverb and whether the dry Release feeds them for longer; this measurement cannot isolate one responsible control.", "後段音效尾音能量較多；請檢查 Delay／Reverb，以及乾聲 Release 是否延長了音效的輸入。此測量不能單獨判定是哪個控制項有錯。"),
}
for k in range(1, 9):
    CONTEXT_CLUES[f"h{k}_low"] = (f"H{k}'s relative contribution is smaller. Try increasing H{k} relative to the other harmonics.", f"H{k} 的相對比例較小，可嘗試增加 H{k} 相對於其他諧波的強度。")
    CONTEXT_CLUES[f"h{k}_high"] = (f"H{k}'s relative contribution is larger. Try reducing H{k} relative to the other harmonics.", f"H{k} 的相對比例較大，可嘗試減少 H{k} 相對於其他諧波的強度。")


def _harmonics(audio, rate, note):
    start = note.start_seconds + min(.35, note.duration_seconds * .4)
    end = note.end_seconds - .04
    segment = audio[round(start * rate):round(end * rate)]
    if len(segment) < 128:
        return None
    window = np.hanning(len(segment))[:, None]
    t = np.arange(len(segment)) / rate
    amplitudes = []
    for k in range(1, 9):
        phase = np.exp(-2j * np.pi * note.frequency_hz * k * t)[:, None]
        projected = np.sum(segment * window * phase, axis=0)
        amplitudes.append(float(np.sqrt(np.mean(np.abs(projected) ** 2))))
    vector = np.array(amplitudes)
    return vector / max(vector.sum(), 1e-20)


def _held_shape(envelope, times, note):
    selection = (times >= note.start_seconds) & (times < note.end_seconds - .02)
    values, clock = envelope[selection], times[selection]
    if len(values) < 12:
        return None
    peak = int(np.argmax(values))
    maximum = max(float(values[peak]), 1e-10)
    rising = values[:peak + 1]
    low, high = (int(np.flatnonzero(rising >= fraction * maximum)[0]) for fraction in (.1, .9))
    plateau = float(np.median(values[clock >= note.end_seconds - .12]))
    decaying = np.flatnonzero(values[peak:] <= plateau + .15 * (maximum - plateau))
    decay = float(clock[peak + decaying[0]] - clock[peak]) if len(decaying) else 0.
    return float(clock[high] - clock[low]), decay, plateau / maximum


def _echo_spacing(envelope, times):
    # Isolated repeats have real quiet gaps. Prefer their rising boundaries to
    # tiny carrier-dependent fluctuations on an otherwise flat RMS plateau.
    active = envelope > .025
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    if len(starts) >= 3:
        gaps = np.diff(times[starts[:6]])
        median = float(np.median(gaps))
        if .07 <= median <= .62 and np.max(np.abs(gaps - median)) <= .015:
            return median
    flux = np.maximum(0., np.diff(envelope))
    if len(flux) < 3 or flux.max() < 1e-6:
        return None
    candidates = np.flatnonzero((flux[1:-1] >= flux[:-2]) & (flux[1:-1] > flux[2:]) & (flux[1:-1] > max(.01, flux.max() * .15))) + 1
    selected = []
    for index in sorted(candidates, key=lambda i: -flux[i]):
        if all(abs(times[index] - times[other]) >= .065 for other in selected):
            selected.append(index)
    onsets = np.sort(times[selected])[:6]
    gaps = np.diff(onsets)
    gaps = gaps[(gaps >= .07) & (gaps <= .62)]
    if len(gaps) < 2:
        return None
    median = float(np.median(gaps))
    if np.max(np.abs(gaps - median)) > .015:
        return None
    return median


def _combined_diagnosis(context, envelopes, times, measurements):
    """Separate provable effect tails from ambiguous wet attack/spectral shapes.

    The synth's longest dry Release is 1.20 s. Energy after the *last*
    note plus that bound cannot be fixed by changing a dry ADSR envelope.
    No reference patch values are consulted here.
    """
    te, pe = envelopes
    last_end = max(note.end_seconds for note in context.sequence.events)
    tail = times >= last_end + 1.24
    body = (times >= context.sequence.events[0].start_seconds) & (times < last_end)
    ratios = [float(np.sum(env[tail] ** 2) / max(np.sum(env[body] ** 2), 1e-20)) for env in (te, pe)]
    evidence = dict(zip(("target_late_effect_ratio", "player_late_effect_ratio"), ratios))
    candidates = []
    if measurements["envelope_error"] > .03 and max(ratios) > .0001:
        log_ratio = float(np.log(max(ratios[1], 1e-8) / max(ratios[0], 1e-8)))
        if abs(log_ratio) > np.log(2):
            candidates.append((min(4., abs(log_ratio)), "effects_tail_long" if log_ratio > 0 else "effects_tail_short"))

    # Use only the first isolated response: later authored note onsets must
    # not be mistaken for echoes of the first note.
    next_starts = [note.start_seconds for note in context.sequence.events[1:]
                   if note.start_seconds > context.sequence.events[0].start_seconds]
    stop = min(next_starts) - .02 if next_starts else times[-1] + .01
    selected = times < stop
    spacing = [_echo_spacing(env[selected], times[selected]) for env in (te, pe)]
    for name, value in zip(("target_echo_interval", "player_echo_interval"), spacing):
        if value is not None:
            evidence[name] = value
    if all(value is not None for value in spacing) and abs(spacing[1] - spacing[0]) > .02:
        candidates.append((5., "echo_slow" if spacing[1] > spacing[0] else "echo_fast"))
    return tuple(code for _, code in sorted(candidates, key=lambda item: -item[0])), evidence


def contextual_diagnosis(context, target, player, rate, envelopes, times, spectra, measurements):
    """Return measured suggestions and numeric evidence. No unique-knob claims."""
    if context is None:
        return (), {}
    if context.profile == "combined":
        return _combined_diagnosis(context, envelopes, times, measurements)
    note = context.sequence.events[0]
    te, pe = envelopes
    evidence, candidates = {}, []
    if context.profile == "harmonics":
        tv, pv = (_harmonics(data, rate, note) for data in (target, player))
        if tv is not None and pv is not None:
            for k, (t, p) in enumerate(zip(tv, pv), 1):
                evidence[f"target_h{k}"] = float(t)
                evidence[f"player_h{k}"] = float(p)
                if f"h{k}" in context.editable and abs(p - t) > .025:
                    candidates.append((abs(p - t), f"h{k}_{'high' if p > t else 'low'}"))
    elif context.profile == "adsr":
        shapes = [_held_shape(env, times, note) for env in (te, pe)]
        if all(shape is not None for shape in shapes):
            for key, t, p, threshold, scale, lower, higher in zip(
                ("attack", "decay", "sustain"), shapes[0], shapes[1], (.025, .04, .06), (.4, .6, 1.),
                ("faster_attack", "decay_fast", "sustain_low"), ("slower_attack", "decay_slow", "sustain_high")):
                evidence[f"{key}_shape_delta"] = float(p - t)
                if abs(p - t) > threshold:
                    candidates.append((abs(p - t) / scale, higher if p > t else lower))
        delta = measurements["player_end_seconds"] - measurements["target_end_seconds"]
        if abs(delta) > .06:
            candidates.append((abs(delta) / 1.2, "longer_tail" if delta > 0 else "shorter_tail"))
    elif context.profile == "filter":
        if measurements["spectrum_error"] > .05:
            candidates.append((1., "filter_shape"))
    else:
        # The isolated-effect cases use a short, fixed dry articulation. This
        # public note boundary plus a guard separates body from effect energy.
        tail = times >= note.end_seconds + .12
        body = (times >= note.start_seconds) & (times < note.end_seconds)
        ratios = [float(np.sum(env[tail] ** 2) / max(np.sum(env[body] ** 2), 1e-20)) for env in (te, pe)]
        evidence["target_effect_energy_ratio"], evidence["player_effect_energy_ratio"] = ratios
        log_ratio = float(np.log(max(ratios[1], 1e-8) / max(ratios[0], 1e-8)))
        if context.profile == "delay":
            spacing = [_echo_spacing(env, times) for env in (te, pe)]
            for name, value in zip(("target_echo_interval", "player_echo_interval"), spacing):
                if value is not None:
                    evidence[name] = value
            if all(value is not None for value in spacing) and abs(spacing[1] - spacing[0]) > .015:
                candidates.append((10., "echo_slow" if spacing[1] > spacing[0] else "echo_fast"))
            elif spacing[0] is not None and spacing[1] is None:
                candidates.append((5., "echo_missing"))
            if abs(log_ratio) > .3:
                candidates.append((min(4., abs(log_ratio)), "echo_strong" if log_ratio > 0 else "echo_weak"))
        else:
            # Compare tail colour on the same tail interval, using power to avoid
            # near-silent late frames dominating the centroid estimate.
            frame_times = np.arange(len(spectra[0])) * 256 / rate
            mask = frame_times >= note.end_seconds + .12
            frequencies = np.fft.rfftfreq(2048, 1 / rate)
            colours = []
            for spectrum in spectra:
                power = np.sum(spectrum[mask] ** 2, axis=0, dtype=np.float64)
                colours.append(float(np.sum(power * frequencies) / max(power.sum(), 1e-20)))
            evidence["target_tail_centroid"], evidence["player_tail_centroid"] = colours
            if min(ratios) > .001 and min(colours) > 1 and abs(np.log(colours[1] / colours[0])) > .18:
                candidates.append((2., "tail_bright" if colours[1] > colours[0] else "tail_dark"))
            if abs(log_ratio) > .3:
                candidates.append((min(3., abs(log_ratio)), "room_strong" if log_ratio > 0 else "room_weak"))
    codes = tuple(code for _, code in sorted(candidates, key=lambda pair: -pair[0]))
    return codes, evidence
