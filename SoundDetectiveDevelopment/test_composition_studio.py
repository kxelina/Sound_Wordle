"""Independent multi-bar scores, instrument routing, editing and actual SC audio."""
import os,sys,json,threading
from dataclasses import replace
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import numpy as np,pytest,soundfile as sf
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtCore import Qt,QPointF
from PySide6.QtTest import QTest
from sound_detective.game.composition import CompositionDraft,CompositionPattern,CompositionNote,METERS
from sound_detective.game.melody import Draft,GridNote,MelodyPattern,MelodySession,load_melody_session,save_melody_session
from sound_detective.audio.models import SoundSettings
from sound_detective.audio.sequence import NoteEvent,NoteSequence
from sound_detective.audio.instruments import INSTRUMENTS,SPACES,instrument_sound,space_sound,space_name
from sound_detective.audio.composition_render import CompositionEngine,CompositionRequest,normalize_wav,publish_wav
from sound_detective.audio.sc_client import RenderCancelled
from sound_detective.audio.preview import PreviewRenderer
from sound_detective.ui.melody import MelodyWindow
from sound_detective.ui.studio import StudioWindow
from test_features import Renderer,Player

@pytest.fixture(scope='session')
def app():
    a=QApplication.instance() or QApplication([])
    for n in ('segoeui.ttf','msyh.ttc','msjh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+n)
    a.setFont(QFont('Microsoft JhengHei UI',10));return a

@pytest.mark.parametrize('meter',METERS)
def test_meter_time_and_unbounded_phrase_grid(meter):
    p=CompositionPattern((CompositionNote(0,1,36),CompositionNote(400,40,84)),100,*meter)
    assert p.steps==100*meter[0]*16//meter[1]
    seq=p.sequence(120)
    assert seq.events[-1].start_seconds==pytest.approx(.07+400*.125)
    assert seq.events[-1].duration_seconds==5
    q=p.with_meter(3,4);assert q.notes==p.notes

def test_chords_cross_bar_lengths_and_no_silent_note_deletion():
    p=CompositionPattern((CompositionNote(0,24,36),CompositionNote(0,24,60),CompositionNote(0,24,84)),3)
    assert len(p.sequence().events)==3
    with pytest.raises(ValueError):replace(p,bars=1)
    with pytest.raises(ValueError):p.with_notes((*p.notes,CompositionNote(1,2,60)))
    assert p.with_meter(6,8).notes==p.notes
    with pytest.raises(ValueError):CompositionNote(0,1,35)
    with pytest.raises(ValueError):CompositionNote(0,1,85)
    with pytest.raises(ValueError):CompositionPattern(bars=True)
    with pytest.raises(ValueError):CompositionDraft(instrument='unknown')
    with pytest.raises(ValueError):p.with_meter(2,0)

def test_legacy_upgrade_exact_backup_and_challenge_isolation(tmp_path):
    s=MelodySession();legacy=s.to_dict();old=Draft(MelodyPattern((GridNote(0,2,64),)),s.free.sound,120)
    legacy['free']=old.to_dict();legacy['mode']='free';path=tmp_path/'舊 創作.json';raw=json.dumps(legacy,ensure_ascii=False).encode();path.write_bytes(raw)
    restored=load_melody_session(path);assert restored.free.sequence==old.sequence
    restored.update(replace(restored.free,pattern=CompositionPattern((CompositionNote(24,20,36),),4),instrument='piano'))
    save_melody_session(path,restored);assert next(tmp_path.glob('*.before-studio-v2-*.json')).read_bytes()==raw
    assert load_melody_session(path).to_dict()==restored.to_dict()
    save_melody_session(path,restored);assert len(list(tmp_path.glob('*.before-studio-v2-*.json')))==1
    restored.set_mode('challenge')
    with pytest.raises(ValueError):restored.update(restored.free)
    assert restored.challenge==Draft() and restored.attempts==0

def test_instrument_and_space_change_separate_components():
    from sound_detective.game.parameters import PARAMETERS
    sound=SoundSettings();hall=space_sound(sound,'hall');guitar=instrument_sound(hall,'guitar')
    assert guitar.effects==hall.effects and guitar.patch==INSTRUMENTS['guitar'][1]
    assert space_sound(guitar,'dry').patch==guitar.patch and space_name(hall)=='hall'
    assert space_name(space_sound(sound,'dry'))=='dry'
    assert not SPACES['hall'][1].delay.enabled and SPACES['hall'][1].reverb.mix<.5
    for instrument in INSTRUMENTS:
        for space in SPACES:
            preset=space_sound(instrument_sound(sound,instrument),space)
            for spec in PARAMETERS.values():spec.validate(spec.get(preset))

def test_damaged_save_is_preserved_before_recovery(app,tmp_path):
    path=tmp_path/'壞.json';path.write_bytes(b'{broken')
    w=MelodyWindow(save_path=path,renderer=Renderer(),player=Player())
    try:
        assert next(tmp_path.glob('*.invalid-*.json')).read_bytes()==b'{broken'
        assert load_melody_session(path).challenge==Draft()
    finally:w.close()

@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_free_controls_preview_undo_meter_and_challenge_gates(app,tmp_path,language):
    r=Renderer();w=MelodyWindow(save_path=tmp_path/'W02.json',renderer=r,player=Player(),language=language);w.resize(1232,624);w.show()
    try:
        w._set_mode('free');app.processEvents();base=w.session.free
        w.instrument_choices.buttons[1].click()
        assert w.session.free.instrument=='piano' and w.session.attempts==0
        request=r.requests[-1][1][0]['instrument'];assert isinstance(request,CompositionRequest) and request.instrument=='piano'
        assert request.sequence.events[0].pitch==60
        w.space_choices.buttons[2].click();assert w.session.free.sound.effects.reverb.active and w.session.free.instrument=='piano'
        assert r.requests[-1][1][0]['instrument'].settings==w.session.free.sound
        w.bars.setValue(8);assert w.session.free.pattern.bars==8
        w.meter_choices.setCurrentIndex(METERS.index((6,8)));assert w.session.free.pattern.steps==96
        w._pattern_changed(CompositionPattern((CompositionNote(24,30,36),CompositionNote(24,30,84)),8,6,8))
        w.bars.setValue(1);assert w.session.free.pattern.bars==8 and w.bars.value()==8
        assert w.piano.pitch.minimum()==36 and w.piano.pitch.maximum()==84 and w.piano.length.maximum()==96
        assert w.piano.roll.height()>=49*22 and w.piano.page.maximum()==8
        w.piano.page.setValue(3);assert w.piano.roll.view_start==24
        w._prepare('export');request=r.requests[-1][1][0]['export'];assert request.export_path.suffix=='.wav' and request.sequence==w.session.free.sequence
        w._set_mode('challenge');assert not w.composition_tools.isVisible() and not w.tempo_panel.isVisible()
        assert w.piano.pitch.minimum()==60 and w.piano.pitch.maximum()==72 and w.piano.start.maximum()==15
        assert w.session.challenge==Draft() and w.session.attempts==0
        w._set_mode('free');assert w.session.free.instrument=='piano'
    finally:w.close();app.processEvents()

def test_free_drag_wide_pitch_and_cross_bar_length(app,tmp_path):
    w=MelodyWindow(save_path=tmp_path/'w.json',renderer=Renderer(),player=Player());w.resize(1200,720);w.show()
    try:
        w._set_mode('free');w._pattern_changed(CompositionPattern((CompositionNote(12,3,60),),4));app.processEvents()
        roll=w.piano.roll;note=roll.pattern.notes[0];point=roll.note_rect(note).center()
        roll.selection=0;roll._drag=(point,note,'right')
        extended=roll._drag_note(point+QPointF(10*roll.cell_width,0));assert extended.length==13
        roll.cancel_drag();roll.replace_selected(extended);assert w.session.free.pattern.notes[0].length==13
        w.edit_bar.undo();assert w.session.free.pattern.notes[0].length==3
        w.piano.pitch.setValue(84);assert w.session.free.pattern.notes[0].pitch==84
        w.piano.pitch.setValue(36);assert w.session.free.pattern.notes[0].pitch==36
        before=roll.width();w.bars.setValue(100000);w.piano.page.setValue(99999);app.processEvents()
        assert roll.width()==before and roll.display_steps<=32
    finally:w.close();app.processEvents()

def test_drag_edges_pan_without_committing_or_leaving_a_timer(app,tmp_path):
    w=MelodyWindow(save_path=tmp_path/'edge.json',renderer=Renderer(),player=Player());w.show()
    try:
        w._set_mode('free');w._pattern_changed(CompositionPattern((CompositionNote(12,3,60),),5));app.processEvents()
        r=w.piano.roll;n=r.pattern.notes[0];r.selection=0;point=r.note_rect(n).center()
        r._drag=(point,n,'right');r._drag_view_start=r.view_start;r._drag_position=point;r._edge_direction=1
        r._edge_pan();assert r.view_start==16 and w.piano.page.value()==2
        assert r._drag_note(point).length==19 and w.session.free.pattern.notes[0].length==3
        r.cancel_drag();assert not r._pan_timer.isActive() and r._drag is None
    finally:w.close()

@pytest.fixture(scope='module')
def engine(tmp_path_factory):return CompositionEngine(runtime_dir=tmp_path_factory.mktemp('instrument-engine'))

@pytest.mark.parametrize('name',['piano','violin','guitar'])
def test_actual_instrument_audio_pitch_and_determinism(engine,tmp_path,name):
    import librosa
    settings=instrument_sound(SoundSettings(),name)
    seq=NoteSequence(tuple(NoteEvent(p,.07+i*1.4,1.) for i,p in enumerate((36,60,84))))
    request=CompositionRequest(settings,seq,name)
    a,b=tmp_path/'a.wav',tmp_path/'b.wav';engine.render_composition(request,a);engine.render_composition(request,b)
    y,sr=sf.read(a);assert np.array_equal(y,sf.read(b)[0]) and sr==44100 and y.shape[1]==2 and .001<np.max(abs(y))<=.90001
    for i,p in enumerate((36,60,84)):
        segment=y[round((.25+i*1.4)*sr):round((.80+i*1.4)*sr)].mean(axis=1)
        f0=librosa.yin(segment,fmin=50,fmax=1300,sr=sr,frame_length=4096,hop_length=512)
        assert abs(1200*np.log2(np.median(f0)/(440*2**((p-69)/12))))<20

def test_long_audio_hall_tail_streaming_export_and_cancel(engine,tmp_path):
    sound=space_sound(instrument_sound(SoundSettings(),'piano'),'hall')
    req=CompositionRequest(sound,NoteSequence((NoteEvent(60,.07,35),)),'piano')
    raw=tmp_path/'長 創作.wav';result=engine.render_composition(req,raw);assert result.duration>35
    normalized=tmp_path/'listening.wav';normalize_wav(raw,normalized)
    y,sr=sf.read(normalized);assert np.max(np.abs(y))<=.90001 and len(y)/sr>35
    exported=tmp_path/'exports/作品.wav';publish_wav(normalized,exported,threading.Event());assert exported.read_bytes()==normalized.read_bytes()
    event=threading.Event();event.set()
    with pytest.raises(RenderCancelled):engine.render_composition(req,tmp_path/'cancel.wav',cancel_event=event)
    assert not (tmp_path/'cancel.wav').exists()
    with pytest.raises(RenderCancelled):publish_wav(normalized,tmp_path/'cancel-export.wav',event)
    assert not (tmp_path/'cancel-export.wav').exists()

def test_preview_cache_isolates_instrument_and_publishes_same_audio(app,tmp_path):
    r=PreviewRenderer(cache_parent=tmp_path);r._composition_engine=CompositionEngine(runtime_dir=tmp_path/'engine')
    try:
        event=threading.Event();seq=NoteSequence((NoteEvent(60,.07,.5),));settings=SoundSettings()
        a,_=r._work({'current':CompositionRequest(settings,seq,'piano')},event)
        b,_=r._work({'current':CompositionRequest(settings,seq,'violin')},event)
        assert a['current'].raw_path!=b['current'].raw_path
        request=CompositionRequest(settings,seq,'piano',tmp_path/'export.wav')
        again,_=r._work({'export':request},event);assert again['export'].cache_hit
        assert request.export_path.read_bytes()==a['current'].listening_path.read_bytes()
        with pytest.raises(ValueError):r.prepare({'a':request,'b':request},match=True)
    finally:r.close()
