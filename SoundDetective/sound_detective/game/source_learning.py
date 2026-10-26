"""Authored difficulty variants and examples that never use a hidden answer."""
from dataclasses import replace
import json
from pathlib import Path

from ..audio.sound_sources import CONTROLS, SourcePatch
from .storage import atomic_json_write

DIFFICULTIES={'beginner':('Beginner · 2 controls','入門 · 2 個控制'),
              'standard':('Standard · 4 controls','標準 · 4 個控制'),
              'advanced':('Advanced · 5 controls','進階 · 5 個控制')}
ORDER={'rain':('density','brightness','drop_length','bed','variation'),
       'bird':('pitch','length','sweep','spacing','brightness'),
       'pluck':('pitch','decay','brightness','body','noise'),
       'static':('brightness','flutter','colour','rate','crackle')}


def with_difficulty(case,difficulty):
    if difficulty not in DIFFICULTIES:raise ValueError('Unknown source difficulty')
    if difficulty=='advanced':return case
    active=ORDER[case.target.recipe][:2 if difficulty=='beginner' else 4]
    values=dict(case.target.values)
    values.update((key,value) for key,value in case.initial.values if key in active)
    title={lang:case.title[lang]+' · '+DIFFICULTIES[difficulty][lang=='zh-Hant'].split(' · ')[0] for lang in ('en','zh-Hant')}
    return replace(case,difficulty=difficulty,editable_parameters=active,title=title,
                   initial=SourcePatch.make(case.target.recipe,values,case.target.seed))


def source_path(base,difficulty):
    base=Path(base)
    if difficulty not in DIFFICULTIES:raise ValueError('Unknown source difficulty')
    return base if difficulty=='advanced' else base.parent/'levels'/f'{base.stem}-{difficulty}.json'


def selected_difficulty(base):
    base=Path(base)
    marker=base.parent/'levels'/f'{base.stem}-selection.json'
    try:
        if marker.stat().st_size>1024:raise ValueError('Oversized source preference')
        value=json.loads(marker.read_text('utf-8'))
        if set(value)!={'difficulty'} or value['difficulty'] not in DIFFICULTIES:raise ValueError('Invalid source preference')
        return value['difficulty']
    except (OSError,ValueError,TypeError,KeyError):
        return 'advanced' if base.exists() else 'beginner'


def remember_difficulty(base,difficulty):
    source_path(base,difficulty)
    base=Path(base)
    atomic_json_write(base.parent/'levels'/f'{base.stem}-selection.json',{'difficulty':difficulty})


def concept_pair(recipe,key):
    """Use neutral, fixed teaching patches, independent of all case targets."""
    specs=CONTROLS[recipe]
    spec=next((s for s in specs if s.key==key),None)
    if spec is None:raise ValueError('Unknown example control')
    values={s.key:s.value_at(.5) for s in specs}
    # Ensure the speed example has audible modulation at both endpoints.
    if recipe=='static':values['flutter']=.65
    low,high=dict(values),dict(values)
    low[key],high[key]=spec.value_at(.2),spec.value_at(.8)
    return SourcePatch.make(recipe,low,101),SourcePatch.make(recipe,high,101)


def example_control(case,patch):
    from .sound_categories import assess_source
    scores=assess_source(case,patch).scores
    return min(scores,key=scores.get)
