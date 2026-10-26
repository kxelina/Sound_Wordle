"""Procedural sound sources for category challenges (no recorded samples).

Recipes are small synthesizers, not finished presets. Every exposed control
changes the generated sound. Fixed seeds make previews and exports repeatable.
"""

from dataclasses import dataclass
import math
from numbers import Real

import numpy as np

from .models import bounded

SOURCE_DURATION = 3.6
SOURCE_VERSION = 1


@dataclass(frozen=True)
class SourceControl:
    key: str
    low: float
    high: float
    step: float
    labels: tuple[str, str]
    help: tuple[str, str]
    directions: tuple[tuple[str, str], tuple[str, str]]
    logarithmic: bool = False
    unit: str = ""

    def position(self, value):
        if self.logarithmic:
            return math.log(value / self.low) / math.log(self.high / self.low)
        return (value - self.low) / (self.high - self.low)

    def value_at(self, position):
        position = min(1., max(0., position))
        value = self.low * (self.high / self.low) ** position if self.logarithmic else self.low + position * (self.high - self.low)
        return min(self.high, max(self.low, round(value / self.step) * self.step))


def control(key, low, high, step, en, zh, help_en, help_zh, low_en, low_zh, high_en, high_zh, *, log=False, unit=""):
    return SourceControl(key, low, high, step, (en, zh), (help_en, help_zh),
                         ((low_en, low_zh), (high_en, high_zh)), log, unit)


CONTROLS = {
    "harmonic": tuple(control(f"h{k}", 0, 1, .01, f"H{k} · {220*k} Hz", f"H{k} · {220*k} Hz",
        f"Changes harmonic {k}, at {220*k} Hz. Relative amplitudes shape the colour; playback level is matched.",
        f"調整第 {k} 次諧波（{220*k} Hz）。各成分的相對強度塑造音色，試聽會匹配電平。",
        "", "", "", "") for k in range(1, 6)),
    "rain": (
        control("density", 3, 25, .5, "Drop density", "雨點密度", "More drops per second make a busier shower.", "每秒雨點越多，雨勢聽起來越密集。", "The rain is too sparse.", "雨點太稀疏。", "The rain is too dense.", "雨點太密集。", unit=" /s"),
        control("brightness", 500, 9000, 10, "Brightness", "明亮度", "Raises the noise filter cutoff; higher values sound sharper.", "提高噪聲濾波截止頻率，聲音會更尖亮。", "The rain sounds too muffled.", "雨聲太悶。", "The rain is too sharp and bright.", "雨聲太尖亮。", log=True, unit=" Hz"),
        control("drop_length", .015, .16, .001, "Drop length", "雨滴長度", "Changes each droplet's fading tail, without reversing the sound.", "改變每顆雨滴的衰減尾音長度。", "The drops end too abruptly.", "雨滴收尾太急促。", "The drops linger too long.", "每顆雨滴拖得太長。", unit=" s"),
        control("bed", 0, .85, .01, "Rain curtain", "背景雨幕", "Mix continuous filtered noise underneath individual drops.", "在獨立雨點下混入連續的濾波噪聲。", "The continuous rain curtain is missing.", "背景連續雨幕太少。", "The continuous wash hides the individual drops.", "背景雨幕太多，蓋住了獨立雨點。"),
        control("variation", 0, 1, .01, "Intensity movement", "雨勢變化", "Adds slow changes in the background rain's intensity.", "讓背景雨勢的強弱隨時間緩慢變化。", "The rain stays too steady.", "雨勢太平穩。", "The rain's intensity fluctuates too much.", "雨勢起伏太大。"),
    ),
    "bird": (
        control("pitch", 60, 100, .1, "Chirp centre", "鳥鳴中心音高", "Moves the whole chirp up or down. MIDI 69 is A4.", "把整段鳥鳴升高或降低；MIDI 69 是 A4。", "The chirp is too low.", "鳥鳴音高太低。", "The chirp is too high.", "鳥鳴音高太高。", unit=" MIDI"),
        control("sweep", -12, 12, .1, "Pitch glide", "音高滑動", "Positive values rise; negative values fall during each chirp.", "正值讓每次鳥鳴上滑，負值讓鳥鳴下滑。", "The chirp needs a stronger upward glide.", "鳥鳴需要更明顯的上滑。", "The chirp rises too steeply.", "鳥鳴上滑太陡。", unit=" st"),
        control("length", .08, .5, .005, "Chirp length", "鳥鳴長度", "Changes the duration of each chirp, keeping its start time.", "改變每次鳥鳴的長度，保持起音位置。", "Each chirp is too short.", "每次鳥鳴太短。", "Each chirp lasts too long.", "每次鳥鳴太長。", unit=" s"),
        control("spacing", .55, 1, .005, "Chirp spacing", "鳥鳴間隔", "Changes the interval between chirp starts.", "改變兩次鳥鳴起音之間的時間。", "The chirps are too close together.", "鳥鳴之間太緊密。", "There is too much space between chirps.", "鳥鳴之間隔得太久。", unit=" s"),
        control("brightness", 0, 1, .01, "Harmonic colour", "諧波色彩", "Mixes upper harmonics into the bird-like whistle.", "在鳥鳴般的哨音中加入高次諧波。", "The chirp is too pure and soft.", "鳥鳴太純、太柔。", "The chirp is too buzzy.", "鳥鳴的高次諧波太多，聽起來太粗。"),
    ),
    "pluck": (
        control("pitch", 48, 84, .1, "Note pitch", "音符音高", "Tunes the vibrating string model; MIDI 60 is C4.", "調整振動弦模型的音高；MIDI 60 是 C4。", "The note is too low.", "音符太低。", "The note is too high.", "音符太高。", unit=" MIDI"),
        control("decay", .15, 2, .01, "String decay", "弦音衰減", "Sets the time for the plucked string to decay by 60 dB.", "設定撥弦聲衰減 60 dB 所需的時間。", "The string fades too quickly.", "弦音消失太快。", "The string rings for too long.", "弦音持續太久。", unit=" s"),
        control("brightness", 0, 1, .01, "String brightness", "弦音明亮度", "Reduces damping to keep more high-frequency detail.", "減少阻尼，保留更多高頻細節。", "The string is too dull.", "弦音太暗。", "The string is too metallic and bright.", "弦音太金屬、太亮。"),
        control("body", 0, 1, .01, "Body tone", "琴身厚度", "Blends a warm fundamental with the plucked string.", "在撥弦聲中混入溫暖的基音。", "The body sounds too thin.", "聲音的厚度不足。", "The body tone dominates the string.", "厚重的基音蓋住了弦音。"),
        control("noise", 0, .5, .01, "Pick noise", "撥弦雜音", "Adds a short noisy attack at the start of the note.", "在音符開頭加入短促的撥弦雜音。", "The noisy pick attack is missing.", "開頭的撥弦雜音太少。", "The attack is too scratchy.", "開頭的刮擦雜音太多。"),
    ),
    "static": (
        control("brightness", 500, 10000, 10, "Noise bandwidth", "噪聲頻寬", "Opens the low-pass filter to reveal more hiss.", "提高低通截止頻率，讓更多高頻嘶聲通過。", "The radio hiss is too dark.", "收音機嘶聲太暗。", "The radio hiss is too bright.", "收音機嘶聲太亮。", log=True, unit=" Hz"),
        control("colour", 0, 1, .01, "Pink-noise blend", "粉紅噪聲比例", "Blends white noise with darker pink noise.", "將白噪聲與較暗的粉紅噪聲混合。", "The noise needs more low-frequency weight.", "噪聲需要更多低頻厚度。", "The noise has too much low-frequency weight.", "噪聲低頻太厚重。"),
        control("flutter", 0, 1, .01, "Flutter depth", "顫動深度", "Changes how strongly the radio noise pulses in loudness.", "改變收音機噪聲音量脈動的強度。", "The noise needs more audible flutter.", "噪聲需要更明顯的顫動。", "The noise pulses too strongly.", "噪聲脈動太強。"),
        control("rate", 1, 15, .1, "Flutter speed", "顫動速度", "Sets the number of amplitude pulses per second.", "設定每秒音量脈動的次數。", "The flutter is too slow.", "顫動太慢。", "The flutter is too fast.", "顫動太快。", unit=" Hz"),
        control("crackle", 0, .8, .01, "Crackle mix", "爆裂聲比例", "Adds short random crackles on top of the radio hiss.", "在收音機嘶聲上加入短促隨機爆裂聲。", "There are too few audible crackles.", "可聽見的爆裂聲太少。", "The crackles overpower the hiss.", "爆裂聲蓋過了背景嘶聲。"),
    ),
}


@dataclass(frozen=True)
class SourcePatch:
    recipe: str
    values: tuple[tuple[str, float], ...]
    seed: int = 2026

    def __post_init__(self):
        if self.recipe not in CONTROLS:
            raise ValueError("Unknown sound source recipe")
        pairs = tuple(self.values)
        if any(not isinstance(pair, (tuple, list)) or len(pair) != 2 for pair in pairs):
            raise ValueError("Invalid source controls")
        data = dict(pairs)
        specs = CONTROLS[self.recipe]
        if len(data) != len(pairs) or set(data) != {spec.key for spec in specs}:
            raise ValueError("Source controls do not match recipe")
        for spec in specs:
            bounded(spec.key, data[spec.key], spec.low, spec.high)
        if type(self.seed) is not int or not 0 <= self.seed <= 2**24:
            raise ValueError("Invalid source seed")
        object.__setattr__(self, "values", tuple((s.key, float(data[s.key])) for s in specs))

    @classmethod
    def make(cls, recipe, values, seed=2026):
        if not isinstance(values, dict):
            raise ValueError("Expected a sound-control object")
        return cls(recipe, tuple(values.items()), seed)

    def to_dict(self):
        return {"recipe": self.recipe, "values": dict(self.values), "seed": self.seed}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"recipe", "values", "seed"}:
            raise ValueError("Invalid procedural sound patch")
        return cls.make(data["recipe"], data["values"], data["seed"])


def source_events(patch):
    """(time, SynthDef, controls) on the same deterministic 3.6-second timeline."""
    v = dict(patch.values)
    rng = np.random.default_rng(patch.seed)
    events = []
    def add(time, name, **args):
        args["seed"] = patch.seed + len(events)
        events.append((float(time), name, args))
    if patch.recipe == "harmonic":
        # Reuse the existing deterministic additive synthesizer, with fixed
        # pitch/envelope and all processors off. No separate audio algorithm.
        events.append((.16, "soundDetective", dict(v, freq=220, attack=.03,
            decay=.12, sustain=.7, release=.25, noteOff=1.2, duration=3.44)))
    elif patch.recipe == "rain":
        add(0, "sdRainBed", cutoff=v["brightness"], amp=v["bed"] * .16,
            variation=v["variation"], duration=SOURCE_DURATION)
        count = round(v["density"] * 3.2)
        for index in range(count):
            at = .12 + (index + rng.uniform(.1, .9)) * 3.2 / count
            add(at, "sdDrop", cutoff=v["brightness"], length=v["drop_length"],
                amp=(1-v["bed"]) * rng.uniform(.09, .18), resonance=rng.uniform(.15, .5))
    elif patch.recipe == "bird":
        for at in np.arange(.16, SOURCE_DURATION-v["length"]-.08, v["spacing"]):
            add(at, "sdChirp", freq=440*2**((v["pitch"]-69)/12), sweep=v["sweep"],
                length=v["length"], brightness=v["brightness"])
    elif patch.recipe == "pluck":
        add(.16, "sdPluck", freq=440*2**((v["pitch"]-69)/12), decay=v["decay"],
            brightness=v["brightness"], body=v["body"], noise=v["noise"], duration=SOURCE_DURATION-.16)
    elif patch.recipe == "static":
        add(0, "sdRadio", cutoff=v["brightness"], colour=v["colour"],
            flutter=v["flutter"], rate=v["rate"], duration=SOURCE_DURATION)
        for at in sorted(rng.uniform(.1, SOURCE_DURATION-.12, 38)):
            add(at, "sdDrop", cutoff=v["brightness"], length=rng.uniform(.002, .012),
                amp=v["crackle"]*rng.uniform(.08, .22), resonance=.8)
    return events


def measure_source(audio, rate=44100):
    """Small, gain-invariant audio summary for the player's analysis display.

    Progress uses authored attribute bands, not a waveform similarity claim.
    Random rain drops are never required to line up sample by sample.
    """
    from scipy import signal
    x = np.asarray(audio, dtype=float)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if x.ndim != 1 or len(x) < 2048 or not np.isfinite(x).all():
        raise ValueError("Expected finite sound-source audio")
    peak = float(np.max(np.abs(x)))
    if peak < 1e-10:
        raise ValueError("Generated sound is silent")
    x = x / peak
    frequencies, _, spectrum = signal.stft(x, fs=rate, window="hann", nperseg=2048, noverlap=1536)
    power = np.abs(spectrum)**2
    energy = power.mean(axis=1)
    centroid = float(np.sum(frequencies*energy) / max(energy.sum(), 1e-15))
    window, hop = round(.02*rate), round(.005*rate)
    frames = np.lib.stride_tricks.sliding_window_view(x, window)[::hop]
    rms = np.sqrt(np.mean(frames**2, axis=1))
    rms /= max(float(rms.max()), 1e-12)
    return {"centroid_hz": centroid, "spectrum_hz": frequencies[::2],
            "spectrum_db": 10*np.log10(np.maximum(energy[::2] / energy.max(), 1e-9)),
            "envelope_seconds": np.arange(len(rms))*hop/rate, "envelope": rms}
