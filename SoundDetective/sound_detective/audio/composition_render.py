"""Long-form SC composition rendering with bounded-memory WAV processing."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,os,shutil,socket,tempfile,time
import numpy as np
import soundfile as sf
from .models import SAMPLE_RATE,SoundSettings
from .sequence import NoteSequence
from .sc_client import (SCEngine,ROOT,PRE_ROLL,PRE_ROLL_FRAMES,MAX_VOICES,EngineError,
    EngineProcessError,RenderResult,check_cancelled,write_score)
from .instruments import INSTRUMENT_IDS

@dataclass(frozen=True)
class CompositionRequest:
    settings:SoundSettings
    sequence:NoteSequence
    instrument:str
    export_path:Path|None=None
    def __post_init__(self):
        if not isinstance(self.settings,SoundSettings) or not isinstance(self.sequence,NoteSequence) or self.instrument not in INSTRUMENT_IDS:raise ValueError('Invalid composition request')
        if self.export_path is not None:
            path=Path(self.export_path).resolve()
            if path.suffix.lower()!='.wav':raise ValueError('Export needs a WAV path')
            object.__setattr__(self,'export_path',path)
    def __iter__(self):return iter((self.settings,self.sequence))
    def __getitem__(self,index):return (self.settings,self.sequence)[index]

def normalize_wav(source,destination,*,target_rms=.10,cancel_event=None):
    """Two passes retain a constant gain and never load a whole song into RAM."""
    peak=energy=count=0
    with sf.SoundFile(source) as f:
        rate=f.samplerate
        for block in f.blocks(blocksize=65536,dtype='float64',always_2d=True):
            check_cancelled(cancel_event);peak=max(peak,float(np.max(np.abs(block))))
            energy+=float(np.sum(block*block));count+=block.size
    if peak<1e-10:raise ValueError('The composition is silent')
    gain=min(target_rms/max(np.sqrt(energy/count),1e-12),.90/peak)
    with sf.SoundFile(source) as src,sf.SoundFile(destination,'w',samplerate=rate,channels=2,subtype='PCM_24') as dest:
        for block in src.blocks(blocksize=65536,dtype='float64',always_2d=True):
            check_cancelled(cancel_event);dest.write(block*gain)

def publish_wav(source,destination,cancel_event):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,suffix='.wav',delete=False) as f:temporary=Path(f.name)
    try:
        with Path(source).open('rb') as src,temporary.open('wb') as dst:
            while block:=src.read(1024*1024):check_cancelled(cancel_event);dst.write(block)
        check_cancelled(cancel_event)
        if destination.exists():raise FileExistsError(str(destination))
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)

class CompositionEngine(SCEngine):
    def _instrument_definition(self,stage,cancel_event):
        source=ROOT/'supercollider/composition.scd'
        fingerprint=hashlib.sha256(source.read_bytes()+str(self.sclang).encode()+str(self.sclang.stat().st_mtime_ns).encode()).hexdigest()[:20]
        cache=self.runtime/('composition-'+fingerprint+'.scsyndef')
        if cache.is_file() and cache.read_bytes().startswith(b'SCgf'):return cache.read_bytes()
        script=stage/source.name;shutil.copy2(source,script)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        for attempt in range(3):
            try:
                log=self._run([str(self.sclang),'-D','-u',str(port),str(script),str(stage)],'instrument-compile.log',90,cancel_event);break
            except EngineProcessError as error:
                if os.name!='nt' or error.exit_code&0xffffffff!=0xc0000008 or attempt==2:raise
        compiled=stage/'sdCompositionVoice.scsyndef'
        if 'SOUND_DETECTIVE_INSTRUMENT_READY' not in log or not compiled.is_file():raise EngineError('Instrument compilation failed: '+log[-1200:])
        data=compiled.read_bytes()
        if not data.startswith(b'SCgf'):raise EngineError('Invalid instrument definition')
        temporary=cache.with_suffix('.tmp');temporary.write_bytes(data);temporary.replace(cache)
        return data

    def render_composition(self,request,output_path,*,overwrite=False,cancel_event=None):
        if not isinstance(request,CompositionRequest):raise TypeError('Expected CompositionRequest')
        settings,sequence=request
        if not sequence.events or settings.patch.is_silent:raise ValueError('Add an audible note first')
        changes=[]
        for n in sequence.events:
            if not 36<=n.pitch<=84:raise ValueError('Composition range is C2–C6')
            changes.extend(((n.start_seconds,1),(n.end_seconds+settings.patch.release,-1)))
        active=0
        for _,delta in sorted(changes):
            active+=delta
            if active>MAX_VOICES:raise ValueError('More than 16 voices overlap, including their release tails. Shorten Release or reduce the chord.')
        destination=Path(output_path).resolve()
        if destination.suffix.lower()!='.wav':raise ValueError('Use a WAV filename')
        if destination.exists() and not overwrite:raise FileExistsError(str(destination))
        base=os.environ.get('SOUND_DETECTIVE_TEMP');started=time.perf_counter()
        if base:Path(base).mkdir(parents=True,exist_ok=True)
        with self._lock,tempfile.TemporaryDirectory(prefix='sd-composition-',dir=base) as temporary:
            stage=Path(temporary)
            if not str(stage).isascii():raise EngineError('Set SOUND_DETECTIVE_TEMP to an ASCII-only temporary folder')
            definitions=self._compile(stage,cancel_event);voice=self._instrument_definition(stage,cancel_event)
            duration=settings.effects.initial_duration(settings.patch,note_off_seconds=sequence.duration_seconds)
            limit=duration+30  # Tail budget relative to the piece, not a song-length cap.
            while True:
                check_cancelled(cancel_event)
                render=self._render_file(request,definitions,voice,stage,duration,cancel_event)
                count=round(duration*SAMPLE_RATE);peak=0.
                with sf.SoundFile(render) as audio:
                    if audio.samplerate!=SAMPLE_RATE or audio.channels!=2 or len(audio)<PRE_ROLL_FRAMES+count:raise EngineError('Unexpected composition WAV format')
                    audio.seek(PRE_ROLL_FRAMES);remaining=count
                    while remaining:
                        check_cancelled(cancel_event);block=audio.read(min(65536,remaining),dtype='float64',always_2d=True)
                        if not np.isfinite(block).all():raise EngineError('Non-finite instrument output')
                        peak=max(peak,float(np.max(np.abs(block))));remaining-=len(block)
                    window=max(.5,settings.effects.delay.time_seconds+.05)
                    audio.seek(PRE_ROLL_FRAMES+count-round(window*SAMPLE_RATE))
                    tail=audio.read(round((window-.03)*SAMPLE_RATE),always_2d=True)
                    tail_rms=float(np.sqrt(np.mean(tail*tail)))
                if tail_rms<=max(peak*.0001,1e-7):break
                if duration>=limit:raise EngineError('The effect tail did not settle; reduce the effect decay')
                duration=min(limit,duration+5)
            if peak<1e-10:raise EngineError('The instrument returned silence')
            gain=min(1.,.9/peak);destination.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent,suffix='.wav',delete=False) as file:export=Path(file.name)
            try:
                with sf.SoundFile(render) as src,sf.SoundFile(export,'w',samplerate=SAMPLE_RATE,channels=2,subtype='PCM_24') as dst:
                    src.seek(PRE_ROLL_FRAMES);position=0
                    while position<count:
                        check_cancelled(cancel_event);block=src.read(min(65536,count-position),dtype='float64',always_2d=True)
                        fade=np.minimum(1.,np.maximum(0.,(count-1-np.arange(position,position+len(block)))/(.02*SAMPLE_RATE)))
                        dst.write(block*gain*fade[:,None]);position+=len(block)
                check_cancelled(cancel_event);export.replace(destination)
            finally:export.unlink(missing_ok=True)
        return RenderResult(destination,duration,SAMPLE_RATE,peak*gain,tail_rms*gain,gain,time.perf_counter()-started)

    def _render_file(self,request,definitions,voice,stage,duration,cancel_event):
        settings,sequence=request;args=settings.synth_arguments(duration);controls=dict(zip(args[::2],args[1::2]))
        names={f'h{i}' for i in range(1,9)}|{'attack','decay','sustain','release'}
        voice_args=[v for k,value in controls.items() if k in names for v in (k,value)]
        fx_args=[v for k,value in controls.items() if k not in names for v in (k,value)]
        events=[(0.,[('/d_recv',[voice]),('/d_recv',[definitions['soundDetectiveEffects']])]),
            (PRE_ROLL,[('/g_new',[100,0,0]),('/s_new',['soundDetectiveEffects',900,1,0,'in',16,*fx_args])])]
        for index,note in enumerate(sequence.events):
            events.append((PRE_ROLL+note.start_seconds,[('/s_new',['sdCompositionVoice',1000+index,1,100,'out',16,*voice_args,
                'instrument',INSTRUMENT_IDS.index(request.instrument),'freq',note.frequency_hz,'noteOff',note.duration_seconds,
                'velocity',note.velocity_gain,'seed',2026+index])]))
        events.append((PRE_ROLL+duration+.01,[('/c_set',[0,0])]))
        score,render=stage/'composition.osc',stage/'composition.wav';render.unlink(missing_ok=True);write_score(events,score)
        self._run([str(self.scsynth),'-N',str(score),'_',str(render),str(SAMPLE_RATE),'WAV','float','-o','2','-i','0','-z','64','-m','65536'],
            'composition-render.log',max(60,duration*4),cancel_event)
        return render
