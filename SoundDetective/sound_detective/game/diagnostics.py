"""Case-aware teaching clues, separate from the audio-only score.

Audio features cannot uniquely distinguish missing effects from a different
dry patch. A structural check uses the case's effect presence/type (never
numeric target knob values) before interpreting those ambiguous features.
"""

from ..audio.matching import CLUES
from .progress import PROGRESS_CLUES


def submission_diagnostics(case, settings, result):
    """Prioritize actionable module checks without changing audio scores.

    Equivalent audible solutions remain valid: passing answers are never
    required to copy the reference's switches. Structural hints only appear
    when a relevant audio component has a meaningful remaining difference.
    """
    if case.passes(result.total, result.spectrum, result.envelope, result.tail):
        return ("close",)
    reference, current = case.reference.effects, settings.effects
    missing = []
    for name in ("filter", "delay", "reverb"):
        if f"{name}_enabled" not in case.editable_parameters:
            continue
        target_fx, player_fx = getattr(reference, name), getattr(current, name)
        target_active = not reference.bypass and (target_fx.enabled if name == "filter" else target_fx.active)
        player_active = not current.bypass and (player_fx.enabled if name == "filter" else player_fx.active)
        difference = 100 - (result.spectrum if name == "filter" else result.envelope)
        if name != "filter":
            difference = max(difference, 100 - result.tail)
        if difference <= 2:
            continue
        if target_active and not player_active:
            code = f"{name}_dry" if player_fx.enabled and not current.bypass and name != "filter" else f"{name}_missing"
            missing.append((difference, code))
        elif player_active and not target_active:
            missing.append((difference, f"{name}_extra"))
        elif name == "filter" and target_active and player_active and target_fx.mode != player_fx.mode and difference > 5:
            missing.append((difference, "filter_family"))
    if missing:
        # Resolve the structural gap first; do not simultaneously tell the
        # player to compensate for missing effects by changing harmonics/ADSR.
        return tuple(code for _, code in sorted(missing, key=lambda item: -item[0]))
    if case.diagnostic_profile == "combined":
        effects = tuple(code for code in result.diagnostics if code in (
            "echo_fast", "echo_slow", "effects_tail_short", "effects_tail_long"))
        if effects:
            return effects
    return tuple(result.diagnostics)


def visible_clue_codes(codes, case):
    """Show all blocking module checks together, otherwise one main issue."""
    structural = tuple(code for code in codes if code in (
        "filter_missing", "filter_extra", "filter_family", "delay_missing", "delay_dry", "delay_extra",
        "reverb_missing", "reverb_dry", "reverb_extra") or code.startswith((
            "progress_filter_enabled_", "progress_delay_enabled_", "progress_reverb_enabled_")))
    return structural[:3 if case.diagnostic_profile == "combined" else 1] if structural else tuple(codes[:1])


def describe_clue(code, case, language="en"):
    zh = language == "zh-Hant"
    if code in PROGRESS_CLUES:
        return PROGRESS_CLUES[code][zh]
    profile = case.diagnostic_profile
    if profile == "filter" and code in ("duller", "brighter", "spectrum", "filter_shape"):
        difference = ("高頻比例較少" if code == "duller" else "高頻比例較多" if code == "brighter" else "頻譜形狀不同") if zh else (
            "There is less high-frequency energy" if code == "duller" else "There is more high-frequency energy" if code == "brighter" else "The spectral shape differs")
        return difference + ("；請比較濾波類型、截止頻率與共振。" if zh else ". Compare filter type, cutoff and resonance.")
    if profile in ("delay", "reverb") and code in ("faster_attack", "slower_attack"):
        return ("起音附近的時間形狀有差異；請比較本關的音效設定。" if zh else
                "The time pattern near the onset differs. Compare this case's effect settings.")
    if profile in ("delay", "reverb") and code in ("longer_tail", "shorter_tail", "envelope"):
        difference = ("尾音較長" if code == "longer_tail" else "尾音較短" if code == "shorter_tail" else "尾音的時間形狀不同") if zh else (
            "The tail lasts longer" if code == "longer_tail" else "The tail ends sooner" if code == "shorter_tail" else "The tail's time pattern differs")
        knobs = ("回聲間隔、衰減時間與濕聲比例" if profile == "delay" else "空間大小、阻尼與濕聲比例") if zh else (
            "Delay spacing, decay and wet mix" if profile == "delay" else "room size, damping and wet mix")
        return difference + (f"；請比較{knobs}。" if zh else f". Compare {knobs}.")
    if profile == "harmonics" and code in ("duller", "brighter", "spectrum"):
        return "諧波比例仍有差異；請比較本關開放的 H 控制項。" if zh else "The harmonic balance differs. Compare the H controls unlocked in this case."
    if profile == "adsr" and code == "envelope":
        return "音量輪廓仍有差異，請比較 Attack、Decay、Sustain 與 Release。" if zh else "The volume contour differs. Compare Attack, Decay, Sustain and Release."
    if profile == "combined" and code in ("duller", "brighter", "spectrum"):
        difference = ("高頻比例較少" if code == "duller" else "高頻比例較多" if code == "brighter" else "頻譜分布仍有差異") if zh else (
            "There is less high-frequency energy" if code == "duller" else "There is more high-frequency energy" if code == "brighter" else "The spectral balance still differs")
        return difference + ("；Filter、Delay／Reverb 和諧波都可能影響此結果。請分別聽重複聲、空間尾音與乾聲明暗，目前無法單憑頻譜判定是哪一項有錯。" if zh else
            ". Filter, Delay/Reverb and harmonics can all affect this result. Compare repeats, room tail and dry brightness separately; the spectrum alone cannot identify the responsible control.")
    if profile == "combined" and code in ("faster_attack", "slower_attack", "envelope", "longer_tail", "shorter_tail"):
        difference = {"faster_attack": ("The onset rises faster", "起音上升較快"),
                      "slower_attack": ("The onset rises more slowly", "起音上升較慢"),
                      "longer_tail": ("The sound ends later", "聲音較晚結束"),
                      "shorter_tail": ("The sound ends sooner", "聲音較早結束"),
                      "envelope": ("The volume contour differs", "音量輪廓有差異")}[code][zh]
        return difference + ("；Delay／Reverb 與 ADSR 都可能造成此差異。先分辨重複聲、空間尾音和乾聲輪廓，暫不能斷定 ADSR 有錯。" if zh else
            ". Delay/Reverb and ADSR can all cause this difference. Compare repeats, room tail and dry articulation separately; this does not establish an ADSR error.")
    return CLUES.get(code, ("The difference has no reliable adjustment direction.", "此差異尚無可靠的調整方向。"))[zh]
