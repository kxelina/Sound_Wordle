"""Muted real-engine feedback and hint-ring checks in the perspective scene."""
import json,os,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(os.environ.get('SOUND_DETECTIVE_QA_GAME',str(Path(__file__).resolve().parents[1]/'SoundDetective'))).resolve()
sys.path.insert(0,str(GAME))
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.ui.studio import StudioWindow
from sound_detective.game.parameters import replace_parameters
from sound_detective.game.melody import Draft,MelodyPattern,GridNote
from sound_detective.game.availability import music_availability
from sound_detective.audio.sc_client import find_executable

app=QApplication([])
for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Microsoft YaHei UI',10))
out=Path(__file__).resolve().parent/'.runtime/submission-guidance-ui';out.mkdir(parents=True,exist_ok=True)
def wait(predicate,seconds=90):
    until=time.monotonic()+seconds
    while not predicate() and time.monotonic()<until:app.processEvents();time.sleep(.01)
    assert predicate(),'Timed out waiting for sound/scene'

with TemporaryDirectory(dir=out) as directory:
    w=StudioWindow(progress_dir=Path(directory),animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    errors=[]
    def activate(cid,device='synth'):
        assert w._accept_case(cid);w._show_page('desk');w._activate_device(device);app.processEvents()
        c=w.controller;c.player.error.connect(errors.append);c.renderer.failed.connect(lambda _,e:errors.append(e));return c
    def point(widget,p):return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(widget.mapTo(w.device_proxy.widget(),p.toPoint()))))
    def click(button):
        QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(button,QPointF(button.rect().center())));app.processEvents()
    def screenshot(name):
        for language in ('en','zh-Hant'):
            w.preferences.language=language;w._translate();app.processEvents()
            w.view.grab().save(str(out/(name+'-'+language+'.png')))
    c=activate('T01')
    c._prepare('compare');wait(lambda:bool(errors) or c.session.attempt_count==1 and c._submission_token is None);assert not errors,errors
    assert '→' not in c.submission_feedback.text()
    near=replace_parameters(c.case.reference,{'release':min(1.2,c.case.reference.patch.release+.30)})
    c._restore_edit(near);c._prepare('compare')
    wait(lambda:bool(errors) or c.session.attempt_count==2 and c._submission_token is None);assert not errors,errors
    assert c.session.last.total>=c.case.hint_threshold and not c.session.solved
    assert 'release' in c.guidance.keys and '→' in c.submission_feedback.text()
    screenshot('tone-feedback-release')
    knob=c.editor.knobs['release'];before=knob.value();a=QPointF(knob.rect().center());b=a+QPointF(0,-12)
    QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(knob,a))
    QTest.mouseMove(w.view.viewport(),pos=point(knob,b))
    QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(knob,b));app.processEvents()
    assert knob.value()!=before and not c.guidance.keys and c.session.attempt_count==2
    c=activate('W09');c._submit();c._hint()
    assert c.guidance.keys and all(c.editor.knobs[k].property('hintTarget') for k in c.guidance.keys)
    screenshot('harmonic-hint-faders')
    c._prepare('current');wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    wait(lambda:c.player.state=='stopped' and c._armed is None)
    c._restore_edit(c.case.target,record=True);c._submit();app.processEvents()
    assert w.page=='review' and '→ 100.0' in w.debrief_panel.submission_feedback.text()
    w.view.grab().save(str(out/'first-clear-delta-zh-Hant.png'))
    c=activate('W07');c._update(Draft(MelodyPattern((GridNote(0,1),)),c.case.initial));c._submit()
    c._update(Draft(MelodyPattern(tuple(GridNote(n.start,n.length,60) for n in c.case.pattern.notes)),c.case.initial));c._submit();c._hint()
    assert c.piano.pitch.property('hintTarget') and c.piano.roll.selection>=0
    screenshot('melody-note-guidance')
    roll=c.piano.roll;note=roll.note_rect(c.session.current.pattern.notes[roll.selection]);a=note.center();b=a+QPointF(0,-roll.ROW)
    before=c.session.current.pattern
    QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(roll,a));QTest.mouseMove(w.view.viewport(),pos=point(roll,b))
    QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(roll,b));app.processEvents()
    assert c.session.current.pattern!=before and c.session.attempts==2
    c=activate('W01');c._submit();c._hint();c.editor.controls['attack'].setValue(.02);c.editor.controls['release'].setValue(.12);c._submit();c._hint()
    assert c.guidance.keys and '→' in c.submission_feedback.text();screenshot('hidden-signal-guidance')
    for button in (c.deck.display,c.stop_button):
        assert c.notebook.rect().contains(button.mapTo(c.notebook,button.rect().bottomRight()))
    music=False
    if music_availability().available:
        c=activate('M01');c._check_repair();assert c.guidance.keys==('filter_enabled',)
        c._submit();assert c.submission_feedback.text();screenshot('music-repair-guidance');music=True
    report={'real_tone_submissions_and_delta':True,'transparent_knob_drag_clears_stale_diagnosis':True,
        'harmonic_fader_hint_rings':True,'real_category_playback_finished':True,'first_clear_delta_visible':True,
        'melody_player_note_selected_and_dragged':True,'hidden_signal_deck_visible':True,
        'optional_music_checked':music,'errors':errors,'volume':0,'game_root':str(GAME),'python_executable':sys.executable,
        'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe'))}
    assert not errors,errors
    w.close();app.processEvents();(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
