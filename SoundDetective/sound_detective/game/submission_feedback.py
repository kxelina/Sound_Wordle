"""Compare recorded submissions without accessing hidden target settings."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ScoreSnapshot:
    total: float
    components: dict
    version: str
    number: int


def describe_submission(current, previous=None, *, language='en', labels=None, details=True,rounding='truncate'):
    """Only consecutive, same-rule submissions form a progress comparison.

    Baselines are real submissions, never synthetic zero scores. Diagnosis
    gates may suppress component names while still allowing total-score deltas.
    """
    zh=language=='zh-Hant';labels=labels or {}
    comparable=(previous is not None and previous.version==current.version
                and previous.number+1==current.number and set(previous.components)==set(current.components))
    if not comparable:
        return '本次提交已記錄，作為後續比較起點。' if zh else 'Submission recorded as a comparison baseline.'
    # Use the displayed precision consistently, including the displayed delta.
    display=(lambda value:round(value,1)) if rounding=='round' else (lambda value:math.floor(value*10)/10)
    before=display(previous.total)
    now=display(current.total)
    delta=round(now-before,1)
    text=(f'比上次：{before:.1f} → {now:.1f}（{delta:+.1f} 分）' if zh else
          f'Previous → now: {before:.1f} → {now:.1f} ({delta:+.1f})')
    if not details or not current.components:return text
    changes={key:current.components[key]-previous.components[key] for key in current.components}
    positive=[key for key,value in changes.items() if value>=.1]
    negative=[key for key,value in changes.items() if value<=-.1]
    if negative and delta<0:
        key=min(negative,key=changes.get);name=labels.get(key,key)
        text+=f'\n{name}退步最多，可檢查本次修改。' if zh else f'\nLargest setback: {name}; review this edit.'
    elif positive:
        key=max(positive,key=changes.get);name=labels.get(key,key)
        text+=f'\n{name}改善最多。' if zh else f'\nMost improved: {name}.'
    elif negative:
        key=min(negative,key=changes.get);name=labels.get(key,key)
        text+=f'\n{name}退步最多，可檢查本次修改。' if zh else f'\nLargest setback: {name}; review this edit.'
    else:
        text+='\n各項進度大致相同。' if zh else '\nComponent progress is unchanged.'
    return text
