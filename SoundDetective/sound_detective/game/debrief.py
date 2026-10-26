"""Read-only, answer-safe snapshots of completed investigations."""

from dataclasses import asdict, dataclass

from ..audio.models import SoundSettings, bounded
from ..audio.sequence import NoteSequence
from ..audio.sound_sources import SourcePatch, CONTROLS


LABELS = {
    'harmonics': ('Harmonic balance', '諧波比例'), 'envelope': ('Envelope', '包絡'),
    'filter': ('Filter', '濾波'), 'delay': ('Echo', '回聲'), 'reverb': ('Room sound', '空間感'),
    'rhythm': ('Rhythm', '節奏'), 'melody': ('Pitch', '音高'), 'timbre': ('Timbre', '音色'),
    'pitch': ('Pitch', '音高'),
}
MEANINGS = {
    'harmonics': ('Harmonics change the balance of the tone components.', '諧波改變聲音各個成分的比例。'),
    'envelope': ('The envelope shapes the beginning, body and ending of each note.', '包絡塑造每個音的起音、持續部分及收尾。'),
    'filter': ('The filter changes which frequency regions pass through.', '濾波改變通過的頻率範圍。'),
    'delay': ('Echo spacing, strength and decay shape repeated sounds.', '回聲的間隔、強度及衰減塑造重複聲。'),
    'reverb': ('Reverb changes the room impression and reverberant tail.', '混響改變空間感及殘響尾音。'),
    'rhythm': ('Note positions and lengths determine the rhythmic shape.', '音符位置和長度決定節奏形狀。'),
    'melody': ('Moving notes vertically changes the melody.', '上下移動音符可以改變旋律。'),
    'timbre': ('Harmonics, envelopes and effects shape the phrase sound.', '諧波、包絡及效果共同塑造樂句音色。'),
    'pitch': ('Pitch correction moves the marked regions toward the intended notes.', '音高校正將標記片段移回預期的音高。'),
}


def tone_clip(settings, sequence):
    if not sequence.events:
        return None
    return {'type': 'tone', 'settings': settings.to_dict(), 'sequence': sequence.to_dict()}


def source_clip(patch):
    return {'type': 'source', 'patch': patch.to_dict()}


def validate_clip(clip):
    if clip is None:
        return
    if not isinstance(clip, dict):
        raise ValueError('Invalid review audio')
    if clip.get('type') == 'tone' and set(clip) == {'type','settings','sequence'}:
        SoundSettings.from_dict(clip['settings'])
        sequence = NoteSequence.from_dict(clip['sequence'])
        if not sequence.events or len(sequence.events)>4096 or sequence.duration_seconds>25:
            raise ValueError('Review phrase is too long')
    elif clip.get('type') == 'source' and set(clip) == {'type','patch'}:
        SourcePatch.from_dict(clip['patch'])
    elif clip.get('type') == 'music' and set(clip) == {'type','settings'}:
        data = clip['settings']
        if not isinstance(data,dict) or set(data)!={'corrections','repair'} or not isinstance(data['corrections'],list) or len(data['corrections'])>64:
            raise ValueError('Invalid music review')
        from .music_repair import RepairSettings
        RepairSettings.from_dict(data['repair'])
        for value in data['corrections']:
            bounded('correction',value,-600,600)
    else:
        raise ValueError('Unsupported review clip')


@dataclass(frozen=True)
class Debrief:
    case_id: str
    kind: str
    title: dict
    attempts: int
    hints: tuple
    seconds: float | None
    before: dict
    after: dict
    clips: dict
    history: tuple
    note: tuple = ('','')

    def __post_init__(self):
        if self.case_id not in (*(f'T{i:02}' for i in range(1,9)),*(f'W{i:02}' for i in range(1,7)),'M01') or self.kind not in ('tone','source','melody','music'):
            raise ValueError('Invalid review case')
        if type(self.attempts) is not int or not 0<=self.attempts<=10**9:
            raise ValueError('Invalid review attempts')
        if set(self.title)!={'en','zh-Hant'} or any(not isinstance(s,str) or len(s)>1000 for s in self.title.values()):
            raise ValueError('Invalid review title')
        if self.seconds is not None:
            bounded('review time',self.seconds,0,365*86400)
        if set(self.before)!=set(self.after) or not 1<=len(self.before)<=12:
            raise ValueError('Invalid review components')
        for value in self.before.values():
            bounded('review score',value,0,100)
        for value in self.after.values():
            if value is not None:
                bounded('review score',value,0,100)
        if set(self.clips)!={'initial','final','target'}:
            raise ValueError('Invalid review roles')
        for clip in self.clips.values():
            validate_clip(clip)
        expected='source' if self.kind=='source' else 'music' if self.kind=='music' else 'tone'
        if self.clips['target'] is None or any(clip is not None and clip['type']!=expected for clip in self.clips.values()):
            raise ValueError('Review audio type does not match the case')
        if (self.kind=='music')!=(self.case_id=='M01') or (self.kind=='melody')!=(self.case_id=='W02'):
            raise ValueError('Review kind does not match the case')
        if (self.kind=='source')!=(self.case_id in ('W03','W04','W05','W06')):
            raise ValueError('Review source kind does not match the case')
        if len(self.history)>1000:
            raise ValueError('Review history is too large')
        for number,score in self.history:
            if type(number) is not int or not 1<=number<=10**9:
                raise ValueError('Invalid review history')
            bounded('history score',score,0,100)
        for pair in (self.hints,self.note):
            if len(pair)!=2 or any(not isinstance(s,str) or len(s)>2500 for s in pair):
                raise ValueError('Invalid review text')
        object.__setattr__(self,'hints',tuple(self.hints))
        object.__setattr__(self,'note',tuple(self.note))
        object.__setattr__(self,'history',tuple(tuple(p) for p in self.history))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or set(data)!=set(cls.__dataclass_fields__):
            raise ValueError('Invalid case review')
        return cls(**data)

    def label(self,key,zh=False):
        if self.kind=='source':
            patch = SourcePatch.from_dict(self.clips['target']['patch'])
            spec = next((s for s in CONTROLS[patch.recipe] if s.key==key),None)
            if spec:
                return spec.labels[zh]
        return LABELS.get(key,(key,key))[zh]

    def explanation(self,key,zh=False):
        if self.kind=='source':
            patch = SourcePatch.from_dict(self.clips['target']['patch'])
            spec = next((s for s in CONTROLS[patch.recipe] if s.key==key),None)
            if spec:
                return spec.help[zh]
        return MEANINGS.get(key,('This part is closer to the case requirements.','這部分更接近案件要求。'))[zh]


def build_debrief(case,session,*,seconds=None):
    """Only completion snapshots may expose hidden reference clips."""
    if not session.solved and not getattr(session,'first_pass',None):
        raise ValueError('Solve the case before opening its review')
    cid=case.id
    hint=('Not recorded','未記錄')
    if cid.startswith('T'):
        from .progress import grade_progress
        record=session.first_pass
        final=case.settings(**record.parameters)
        before,after=grade_progress(case,case.initial).modules,grade_progress(case,final).modules
        clips={'initial':tone_clip(case.initial,case.sequence),'final':tone_clip(final,case.sequence),'target':tone_clip(case.reference,case.sequence)}
        rows=tuple((r.number,r.total) for r in session.records if r.run==record.run and r.number<=record.number)
        return Debrief(cid,'tone',case.title,record.number,hint,record.elapsed_seconds,before,after,clips,rows)
    if cid=='W01':
        from .hidden_sound import assess,settings_from_parameters
        final=settings_from_parameters(session.solution)
        before=dict(zip(('envelope','harmonics','delay'),assess(case.initial).scores))
        after=dict(zip(before,assess(final).scores))
        rows=tuple((r['number'],assess(settings_from_parameters(r['parameters'])).total) for r in session.records)
        clips={'initial':tone_clip(case.initial,case.sequence),'final':tone_clip(final,case.sequence),'target':tone_clip(case.reference,case.sequence)}
        return Debrief(cid,'tone',case.title,session.attempts,('Hint tiers by stage: '+' / '.join(map(str,session.hints)),'各階段提示層級：'+' / '.join(map(str,session.hints))),seconds,before,after,clips,rows)
    if cid=='W02':
        if session.mode=='free':
            raise ValueError('Free composition is not graded')
        from .melody import Draft,compare_draft
        final=Draft.from_dict(session.solution)
        initial=Draft()
        before=dict(zip(('rhythm','melody','timbre'),compare_draft(initial).scores))
        after=dict(zip(before,compare_draft(final).scores))
        rows=tuple((r['number'],compare_draft(Draft.from_dict(r['draft'])).total) for r in session.records)
        clips={'initial':None,'final':tone_clip(final.sound,final.sequence),'target':tone_clip(case.reference,case.sequence)}
        note=('The starting draft was empty, so there is no starting audio.','起始草稿沒有音符，因此沒有起點聲音。')
        return Debrief(cid,'melody',case.title,session.attempts,('Hint tiers by stage: '+' / '.join(map(str,session.hints)),'各階段提示層級：'+' / '.join(map(str,session.hints))),seconds,before,after,clips,rows,note)
    if cid.startswith('W'):
        from .sound_categories import assess_source
        records=[r for r in session.records if assess_source(case,SourcePatch.from_dict(r['patch'])).passed]
        record=records[0] if records else None
        final=SourcePatch.from_dict(record['patch']) if record else None
        before=assess_source(case,case.initial).scores
        after=assess_source(case,final).scores if final else {k:None for k in before}
        clips={'initial':source_clip(case.initial),'final':source_clip(final) if final else None,'target':source_clip(case.target)}
        rows=tuple((r['number'],r['score']) for r in session.records if record is None or r['number']<=record['number'])
        note=('Only the retained submission history is shown.','僅顯示仍保留的提交記錄。')
        if final is None:
            note=('The historical cleared answer is no longer retained. Final audio and component values are unavailable.','歷史通關答案已不在保留記錄中，無法試聽最終答案或還原當時的分項分數。')
        return Debrief(cid,'source',case.title,record['number'] if record else session.attempts,('Highest clue tier: '+str(session.hints),'最高提示層級：'+str(session.hints)),seconds,before,after,clips,rows,note)
    if cid=='M01':
        from .music_cases import MusicSettings
        from .music_repair import RepairSettings,initial_estimates,check_repair
        initial=MusicSettings((0,)*len(case.regions),RepairSettings(initial_estimates()))
        final=session.render_settings()
        before={m.group:100*m.fraction for m in check_repair(case,initial).modules}
        after={m.group:100*m.fraction for m in check_repair(case,final).modules}
        clip=lambda s:{'type':'music','settings':s.to_dict()}
        clips={'initial':clip(initial),'final':clip(final),'target':clip(final)}
        note=('Completed repair stages lock in their recovered sound. The graph shows the starting and completed component estimates; intermediate submission scores were not retained. The target audition uses the original excerpt.','已完成的修復步驟會固定還原結果；圖表顯示起點與結案的分項估計，沒有補造未保留的中途提交分數。目標試聽使用原曲片段。')
        return Debrief(cid,'music',case.title,session.attempts,hint,seconds,before,after,clips,(),note)
    raise ValueError('Unknown review case')
