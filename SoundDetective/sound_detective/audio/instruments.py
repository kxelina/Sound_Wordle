"""Original synthesized instrument patches and independent space presets."""
from dataclasses import replace
from .models import SynthPatch,EffectSettings,FilterSettings,DelaySettings,ReverbSettings

INSTRUMENTS={
    'synth':(('Synthesizer','合成器'),SynthPatch()),
    'piano':(('Piano','鋼琴'),SynthPatch((1,.48,.24,.17,.09,.06,.03,.02),.01,.45,.75,.32)),
    'violin':(('Violin','小提琴'),SynthPatch((1,.68,.48,.34,.23,.15,.10,.07),.12,.25,.85,.23)),
    'guitar':(('Guitar','吉他'),SynthPatch((1,.46,.30,.13,.10,.06,.04,.02),.01,.40,.72,.22)),
}
INSTRUMENT_IDS=tuple(INSTRUMENTS)
SPACES={
    'dry':(('Dry','乾聲'),EffectSettings()),
    'room':(('Small room','小房間'),EffectSettings(reverb=ReverbSettings(True,.23,.65,.13))),
    'hall':(('Concert hall','音樂廳'),EffectSettings(reverb=ReverbSettings(True,.82,.35,.33))),
    'echo':(('Echo space','回聲空間'),EffectSettings(delay=DelaySettings(True,.38,2.0,.22),reverb=ReverbSettings(True,.72,.45,.25))),
}

def instrument_sound(settings,name):
    if name not in INSTRUMENTS:raise ValueError('Unknown instrument')
    return replace(settings,patch=INSTRUMENTS[name][1])

def space_sound(settings,name):
    if name not in SPACES:raise ValueError('Unknown space preset')
    return replace(settings,effects=SPACES[name][1])

def space_name(settings):
    fx=settings.effects
    if fx.bypass or not fx.filter.enabled and not fx.delay.active and not fx.reverb.active:return 'dry'
    return next((key for key,(_,fx) in SPACES.items() if settings.effects==fx),'custom')
