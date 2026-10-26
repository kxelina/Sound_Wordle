"""Directional reconstruction progress for authored synthesizer puzzles.

This is intentionally a distance to the answer's controls, not an acoustic
similarity estimate. Audio matching remains available in the development bench.
"""

from dataclasses import dataclass
import math

from .parameters import GROUPS, PARAMETERS


PROGRESS_VERSION = "answer-progress-v2"
PROGRESS_CLUES = {"progress_close": (
    "The reconstruction has reached this case's target tolerance.",
    "還原進度已達到本案的目標容差。")}
for key, parameter in PARAMETERS.items():
    if parameter.kind == "bool":
        module = GROUPS[parameter.group][0]
        for direction, en, zh in (("on", "Enable", "開啟"), ("off", "Disable", "關閉")):
            PROGRESS_CLUES[f"progress_{key}_{direction}"] = (
                f"{en} {module} to match the target configuration before adjusting its knobs.",
                f"先{zh} {module}，使開關與目標設定一致，再調整其旋鈕。")
    elif parameter.kind == "choice":
        for value, en, zh in (("lowpass", "low-pass", "低通"), ("highpass", "high-pass", "高通")):
            PROGRESS_CLUES[f"progress_{key}_{value}"] = (
                f"Switch Filter to {en}. Compare cutoff and resonance after its type matches.",
                f"將 Filter 切換為{zh}；類型一致後，再比較截止頻率與共振。")
    else:
        for direction, en, zh in (("up", "Increase", "提高"), ("down", "Decrease", "降低")):
            label = "Cutoff (Hz)" if key == "cutoff_hz" else parameter.labels[0]
            zh_label = "截止頻率（Hz）" if key == "cutoff_hz" else parameter.labels[1]
            PROGRESS_CLUES[f"progress_{key}_{direction}"] = (
                f"{en} {label}: it is {'below' if direction == 'up' else 'above'} the target setting.",
                f"目前的{zh_label}比目標{'低' if direction == 'up' else '高'}，可嘗試{zh}。")


@dataclass(frozen=True)
class ProgressResult:
    total: float
    modules: dict[str, float]
    errors: dict[str, float]
    diagnostics: tuple[str, ...]
    passed: bool
    version: str = PROGRESS_VERSION


def progress_passes(case, total, modules):
    expected = {PARAMETERS[key].group for key in case.editable_parameters}
    return (set(modules) == expected and all(math.isfinite(value) and 0 <= value <= 100 for value in modules.values())
            and total >= case.comparison.pass_score
            and min(modules.values()) >= case.comparison.component_floor)


def grade_progress(case, settings):
    """Moving any effective numeric control toward its target cannot lower score.

    Modules have equal weights, regardless of their number of knobs. A wrong
    editable switch scores zero; correcting it earns at least 25 module points.
    A wrong filter family allows up to 20 points for its numeric knobs;
    correcting it earns at least 40. Inactive effect knobs are ignored.
    Thus switching on a required effect or correcting its family never loses
    points just because the newly exposed numeric knobs still need adjustment.
    """
    if settings.patch.is_silent:
        raise ValueError("Cannot score silence; add a harmonic and preview again")
    values, target = case.parameters(settings), case.parameters(case.reference)
    if case.settings(**values) != settings:
        raise ValueError("Progress settings changed a locked case control")
    groups = {name: [key for key in values if PARAMETERS[key].group == name]
              for name in GROUPS if any(PARAMETERS[key].group == name for key in values)}
    modules, errors, clues = {}, {}, {}
    for group, keys in groups.items():
        enabled_key = f"{group}_enabled"
        target_fx = getattr(case.reference.effects, group, None)
        if enabled_key in keys and values[enabled_key] != target[enabled_key]:
            modules[group], errors[enabled_key] = 0., 1.
            clues[group] = (f"progress_{enabled_key}_{'on' if target[enabled_key] else 'off'}",)
            continue
        if target_fx is not None and not target_fx.enabled:
            modules[group], clues[group] = 100., ()
            continue
        wrong_family = "filter_mode" in keys and values["filter_mode"] != target["filter_mode"]
        if wrong_family:
            errors["filter_mode"] = 1.
        candidates = []
        for key in keys:
            parameter = PARAMETERS[key]
            if parameter.kind in ("bool", "choice"):
                continue
            # A target with no wet signal has no meaningful room/spacing knobs.
            if group in ("delay", "reverb") and target_fx.mix == 0 and key != f"{group}_mix":
                continue
            delta = values[key] - target[key]
            error = abs(delta) / (parameter.high - parameter.low)
            errors[key] = error
            if error > 1e-12:
                candidates.append((error, f"progress_{key}_{'down' if delta > 0 else 'up'}"))
        numeric_errors = [errors[key] for key in keys if key in errors and PARAMETERS[key].kind not in ("bool", "choice")]
        distance = .5 * (sum(numeric_errors) / len(numeric_errors) + max(numeric_errors)) if numeric_errors else 0.
        score = 100 * (1 - distance) ** 2
        if "filter_mode" in keys:
            score = .20 * score if wrong_family else 40 + .60 * score
        if enabled_key in keys:
            score = 25 + .75 * score
        modules[group] = float(score)
        clues[group] = ((f"progress_filter_mode_{target['filter_mode']}",) if wrong_family
                        else tuple(code for _, code in sorted(candidates, key=lambda item: -item[0])))
    total = float(sum(modules.values()) / len(modules))
    passed = progress_passes(case, total, modules)
    # One main adjustment per module, worst module first. No hint in a mostly
    # correct module should distract from a missing effect elsewhere.
    codes = tuple(clues[group][0] for group in sorted(groups, key=lambda name: modules[name]) if clues[group])
    return ProgressResult(total, modules, errors, ("progress_close",) if passed else codes or ("progress_close",), passed)
