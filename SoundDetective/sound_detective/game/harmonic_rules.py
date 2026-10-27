"""Grouped harmonic-power requirements, independent of absolute output level.

These are analytic features of the five fixed-frequency sinusoidal components,
not perceptually calibrated similarity or a recovered unique slider preset.
"""
from ..audio.sound_sources import SourceControl

VERSION = 'harmonic-groups-v1'
DISTANCE_SCALES = {'odd_upper': .4, 'upper_power': .4, 'spectral_center': 1.5}
FEATURES = (
    SourceControl('odd_upper', 0, 1, .01, ('Odd share of upper harmonics', '高次諧波的奇數比例'),
        ('Compares H3 + H5 power with all H2–H5 power; H1 is excluded.', '比較 H3＋H5 能量佔 H2–H5 的比例，不把 H1 計入。'), (('', ''), ('', ''))),
    SourceControl('upper_power', 0, 1, .01, ('Upper-harmonic energy', '高次諧波能量'),
        ('Compares H2–H5 power with all five components, so a pure sine cannot satisfy this task.', '比較 H2–H5 能量佔全部五個成分的比例，純正弦無法滿足本案要求。'), (('', ''), ('', ''))),
    SourceControl('spectral_center', 1, 5, .01, ('Spectral centre / fundamental', '頻譜中心／基頻'),
        ('A power-weighted frequency centre, measured in multiples of the fixed 220 Hz fundamental.', '依能量加權的頻率中心，以固定 220 Hz 基頻的倍數表示。'), (('', ''), ('', ''))),
)


def features(patch):
    values = dict(patch.values)
    power = [values[f'h{k}']**2 for k in range(1, 6)]
    total, upper = sum(power), sum(power[1:])
    return {'odd_upper': (power[2] + power[4])/upper if upper else 0.,
            'upper_power': upper/total if total else 0.,
            'spectral_center': sum((k+1)*p for k,p in enumerate(power))/total if total else 1.}


def is_silent(patch):
    return patch.recipe == 'harmonic' and not any(value for _, value in patch.values)


def problem_key(patch, result):
    # Odd/even balance is undefined for a pure sine and unhelpful when upper
    # power is negligible. Establish audible upper components first.
    if features(patch)['upper_power'] < .02:
        return 'upper_power'
    return min(result.scores, key=result.scores.get)


def suggested_control(case, patch, result):
    return guidance_keys(case,patch,result)[0]


def guidance_keys(case, patch, result):
    key = problem_key(patch,result)
    values=dict(patch.values);direction=result.directions[key]
    if key=='odd_upper':
        candidates=('h2','h4')
        possible=lambda k:values[k]>0 if direction<0 else values[k]<1
    elif key=='upper_power':
        candidates=('h3','h5','h2','h4')
        possible=lambda k:values[k]<1 if direction<0 else values[k]>0
    else:
        candidates=('h5','h4','h3','h2')
        possible=lambda k:values[k]<1 if direction<0 else values[k]>0 and int(k[1:])>features(patch)['spectral_center']
    available=tuple(k for k in candidates if k in case.editable_parameters and possible(k))
    if available:return available[:2]
    fallback=tuple(k for k in case.editable_parameters if k!='h1')
    return fallback[:1] or ('h1',)


def clue(case, patch, result, tier, language):
    zh = language == 'zh-Hant'
    if is_silent(patch):
        return ('目前為靜音。先提高至少一根諧波推桿，再試聽或提交。' if zh else
                'This is silence. Raise at least one harmonic before listening or submitting.')
    if result.passed:
        return ('音色要求已達標；提交即可記錄。參考推桿不是唯一答案。' if zh else
                'The sound requirements are met. Submit to record it; the reference sliders are only one possible answer.')
    key = problem_key(patch,result)
    direction = result.directions[key]
    texts = {
        ('odd_upper', -1): ('The upper harmonics have too much even-numbered weight for the hollow signal.', '高次諧波中偶數成分太突出，空心感不足。'),
        ('odd_upper', 1): ('The upper harmonics need a little more even-numbered weight.', '高次諧波還需要一點偶數成分。'),
        ('upper_power', -1): ('It is too close to a pure whistle; some upper-harmonic energy is missing.', '目前太接近純哨音，還缺少一些高次諧波能量。'),
        ('upper_power', 1): ('The upper harmonics overpower the fundamental; the buzz is too strong.', '高次諧波蓋過基音，嗡聲太強。'),
        ('spectral_center', -1): ('The frequency balance is too low and dull.', '頻率重心偏低，音色太悶。'),
        ('spectral_center', 1): ('The frequency balance is too high and sharp.', '頻率重心偏高，音色太尖銳。'),
    }
    text = texts[(key, direction)][zh]
    if tier >= 2:
        odd = 'H3 / H5' if 'h5' in case.editable_parameters else 'H3'
        even = 'H2 / H4' if 'h4' in case.editable_parameters else 'H2'
        actions = {
            ('odd_upper', -1): (f'Try more {odd} or less {even}; compare the colour, not loudness.', f'可增加 {odd} 或減少 {even}；比較音色，而非響度。'),
            ('odd_upper', 1): (f'Try more {even} relative to {odd}.', f'可提高 {even} 相對於 {odd} 的比例。'),
            ('upper_power', -1): ('Raise the unlocked upper harmonics relative to H1.', '提高已開放的高次諧波相對於 H1 的比例。'),
            ('upper_power', 1): ('Lower the unlocked upper harmonics relative to H1.', '降低已開放的高次諧波相對於 H1 的比例。'),
            ('spectral_center', -1): ('Move some energy toward higher unlocked harmonics.', '將部分能量移向已開放的較高次諧波。'),
            ('spectral_center', 1): ('Move some energy toward lower unlocked harmonics.', '將部分能量移向已開放的較低次諧波。'),
        }
        text += ' ' + actions[(key,direction)][zh]
    if tier >= 3:
        spec = next(s for s in FEATURES if s.key == key)
        low,high = case.bands[key]
        text += (f' {spec.labels[zh]}：{low:.2f}–{high:.2f}。' if zh else
                 f' Accepted band for {spec.labels[zh]}: {low:.2f}–{high:.2f}.')
    return text
