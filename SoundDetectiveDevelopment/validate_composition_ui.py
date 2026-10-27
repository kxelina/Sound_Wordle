"""Muted scene-pointer test of instrument selection, long-note editing and export."""
import json,os,sys,time,shutil
from pathlib import Path
from tempfile import TemporaryDirectory
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(os.environ.get('SOUND_DETECTIVE_QA_GAME',str(Path(__file__).resolve().parents[1]/'SoundDetective'))).resolve()
sys.path.insert(0,str(GAME))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from sound_detective.ui.studio import StudioWindow
from sound_detective.audio.sc_client import find_executable
from sound_detective.game.melody import load_melody_session
import soundfile as sf

app=QApplication([])
for n in ('segoeui.ttf','msyh.ttc','msjh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+n)
app.setFont(QFont('Microsoft JhengHei UI',10))
out=Path(os.environ.get('SOUND_DETECTIVE_QA_OUTPUT',str(Path(__file__).resolve().parent/'.runtime/composition-ui'))).resolve();out.mkdir(parents=True,exist_ok=True)
def wait(predicate,seconds=90):
    until=time.monotonic()+seconds
    while not predicate() and time.monotonic()<until:app.processEvents();time.sleep(.01)
    assert predicate(),'Timed out waiting for composition audio'
with TemporaryDirectory(dir=out) as folder:
    w=StudioWindow(progress_dir=Path(folder),animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    assert w.open_free_composition();w._show_page('desk');w._activate_device('synth');app.processEvents();c=w.controller
    errors=[];c.renderer.failed.connect(lambda _,e:errors.append(e));c.player.error.connect(errors.append)
    def point(widget,p):return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(widget.mapTo(w.device_proxy.widget(),p.toPoint()))))
    def click(widget):QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(widget,QPointF(widget.rect().center())));app.processEvents()
    click(c.instrument_choices.buttons[1]);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    assert c.session.free.instrument=='piano' and not c.session.free.pattern.notes
    click(c.deck.stop);wait(lambda:c.player.state=='stopped')
    for _ in range(3):click(c.add_bar)
    click(c.meter_choices.buttons[1]);assert c.session.free.pattern.bars==4 and c.session.free.pattern.numerator==3
    click(c.piano.add_button);app.processEvents();r=c.piano.roll;n=c.session.free.pattern.notes[0]
    rect=r.note_rect(n);a=QPointF(rect.right()-2,rect.center().y());b=a+QPointF(13*r.cell_width,0)
    QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(r,a));QTest.mouseMove(w.view.viewport(),pos=point(r,b));QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(r,b));app.processEvents()
    assert c.session.free.pattern.notes[0].length==14
    for text,pitch in (('C2',36),('C6',84)):
        field=c.piano.pitch.lineEdit();QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(field,QPointF(field.rect().center())))
        QTest.keyClick(field,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier);QTest.keyClicks(field,text);QTest.keyClick(field,Qt.Key.Key_Return);app.processEvents()
        assert c.session.free.pattern.notes[0].pitch==pitch
    p=r.point_for(0,60);c.piano.viewport.ensureVisible(round(p.x()),round(p.y()),30,30);app.processEvents()
    QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(r,p));app.processEvents()
    assert len(c.session.free.pattern.notes)==2 and c.session.free.pattern.notes[0].start==c.session.free.pattern.notes[1].start==0
    notes=c.session.free.pattern.notes;click(c.space_choices.buttons[2]);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    assert c.session.free.pattern.notes==notes and c.session.free.sound.effects.reverb.active
    click(c.deck.stop);wait(lambda:c.player.state=='stopped')
    for language in ('en','zh-Hant'):
        w.preferences.language=language;w._translate();app.processEvents();w.view.grab().save(str(out/('composition-'+language+'.png')))
    click(c.export_button);wait(lambda:bool(errors) or c.status.text().startswith(('Exported:','已匯出：')));assert not errors,errors
    export=next((Path(folder)/'wordle/exports').glob('*.wav'));info=sf.info(export)
    assert info.samplerate==44100 and info.channels==2 and info.duration>c.session.free.sequence.duration_seconds+1
    shutil.copy2(export,out/'piano-hall-chord.wav')
    click(c.space_choices.buttons[3]);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    assert c.session.free.sound.effects.delay.active
    click(c.deck.stop);wait(lambda:c.player.state=='stopped')
    click(c.instrument_choices.buttons[2]);click(c.instrument_choices.buttons[3]);wait(lambda:bool(errors) or c._armed is None and c.player.state=='playing');assert not errors,errors
    assert c.session.free.instrument=='guitar' and c.session.free.pattern.notes==notes
    click(c.deck.stop);wait(lambda:c.player.state=='stopped')
    saved=c.session.free.to_dict();path=c.save_path;w.close();app.processEvents();assert load_melody_session(path).free.to_dict()==saved
    report={'actual_scene_instrument_autoplay':True,'cross_bar_edge_drag':True,'typed_C2_and_C6':True,'chord_creation':True,
        'meter_and_bar_controls':True,'space_preserves_notes':True,'rapid_instrument_change_latest_wins':True,
        'wav_with_effect_tail':True,'echo_scene_audition':True,'saved_composition_reloaded':True,'volume':0,'errors':errors,
        'game_root':str(GAME),'python_executable':sys.executable,'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe'))}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False),flush=True)
