"""Independent, multi-bar composition data; challenge grids remain unchanged."""
from dataclasses import dataclass,field,replace
from ..audio.models import SoundSettings
from ..audio.sequence import NoteEvent,NoteSequence
from ..audio.instruments import INSTRUMENTS

LOW,HIGH=36,84  # C2–C6.
METERS=((2,4),(3,4),(4,4),(5,4),(6,8),(7,8),(9,8),(12,8))

def integer(value,low,high,name):
    if type(value) is not int or not low<=value<=high:raise ValueError(f'Invalid {name}')

@dataclass(frozen=True,order=True)
class CompositionNote:
    start:int
    length:int
    pitch:int=60
    def __post_init__(self):
        integer(self.start,0,2**31-1,'start');integer(self.length,1,2**31-1,'length');integer(self.pitch,LOW,HIGH,'pitch')
    def to_dict(self):return {'start':self.start,'length':self.length,'pitch':self.pitch}

@dataclass(frozen=True)
class CompositionPattern:
    notes:tuple=()
    bars:int=1
    numerator:int=4
    denominator:int=4
    def __post_init__(self):
        integer(self.bars,1,1_000_000,'bar count')
        if type(self.numerator) is not int or type(self.denominator) is not int or (self.numerator,self.denominator) not in METERS:raise ValueError('Unsupported meter')
        if not isinstance(self.notes,(tuple,list)) or any(not isinstance(n,CompositionNote) for n in self.notes):raise ValueError('Invalid composition notes')
        notes=tuple(sorted(self.notes));ends={}
        for n in notes:
            if n.start+n.length>self.steps:raise ValueError('Add bars before extending a note beyond the timeline')
            if ends.get(n.pitch,0)>n.start:raise ValueError('Notes at the same pitch cannot overlap')
            ends[n.pitch]=n.start+n.length
        object.__setattr__(self,'notes',notes)
    @property
    def steps_per_bar(self):return self.numerator*16//self.denominator
    @property
    def steps(self):return self.bars*self.steps_per_bar
    def with_notes(self,notes):return replace(self,notes=tuple(CompositionNote(n.start,n.length,n.pitch) for n in notes))
    def with_meter(self,numerator,denominator):
        if (numerator,denominator) not in METERS:raise ValueError('Unsupported meter')
        capacity=numerator*16//denominator
        needed=max((n.start+n.length for n in self.notes),default=0)
        return replace(self,numerator=numerator,denominator=denominator,bars=max(self.bars,(needed+capacity-1)//capacity))
    def sequence(self,tempo=100):
        integer(tempo,60,160,'tempo')
        return NoteSequence(tuple(NoteEvent(n.pitch,.07+n.start*60/tempo/4,n.length*60/tempo/4,100) for n in self.notes))

def initial_sound():
    from .hidden_sound import load_hidden_case
    return load_hidden_case().initial

@dataclass(frozen=True)
class CompositionDraft:
    pattern:CompositionPattern=field(default_factory=CompositionPattern)
    sound:SoundSettings=field(default_factory=initial_sound)
    tempo:int=100
    instrument:str='synth'
    def __post_init__(self):
        if not isinstance(self.pattern,CompositionPattern) or not isinstance(self.sound,SoundSettings):raise ValueError('Invalid composition')
        integer(self.tempo,60,160,'tempo')
        if self.instrument not in INSTRUMENTS:raise ValueError('Unknown instrument')
    @property
    def sequence(self):return self.pattern.sequence(self.tempo)
    def to_dict(self):
        return {'schema_version':2,'notes':[n.to_dict() for n in self.pattern.notes],
            'bars':self.pattern.bars,'meter':[self.pattern.numerator,self.pattern.denominator],
            'sound':self.sound.to_dict(),'tempo':self.tempo,'instrument':self.instrument}
    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict):raise ValueError('Invalid composition save')
        if set(data)=={'notes','sound','tempo'}:
            from .melody import Draft
            return cls.from_legacy(Draft.from_dict(data))
        if set(data)!={'schema_version','notes','bars','meter','sound','tempo','instrument'} or type(data['schema_version']) is not int or data['schema_version']!=2:raise ValueError('Unsupported composition save')
        if not isinstance(data['notes'],list) or not isinstance(data['meter'],list) or len(data['meter'])!=2:raise ValueError('Invalid composition layout')
        notes=[]
        for n in data['notes']:
            if not isinstance(n,dict) or set(n)!={'start','length','pitch'}:raise ValueError('Invalid composition note')
            notes.append(CompositionNote(**n))
        return cls(CompositionPattern(tuple(notes),data['bars'],*data['meter']),SoundSettings.from_dict(data['sound']),data['tempo'],data['instrument'])
    @classmethod
    def from_legacy(cls,draft):
        return cls(CompositionPattern(tuple(CompositionNote(n.start,n.length,n.pitch) for n in draft.pattern.notes)),draft.sound,draft.tempo)
