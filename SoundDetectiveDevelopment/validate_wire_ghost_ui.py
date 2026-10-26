"""Muted real-engine scene-pointer verification of the W09 harmonic faders."""
import json,os,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(os.environ.get('SOUND_DETECTIVE_QA_GAME',str(Path(__file__).resolve().parents[1]/'SoundDetective'))).resolve()
sys.path.insert(0,str(GAME))
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QStyle,QStyleOptionSlider
from sound_detective.ui.studio import StudioWindow
from sound_detective.audio.sc_client import find_executable
from sound_detective.game.sound_categories import assess_source,load_source_session
import soundfile as sf

app=QApplication([])
for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Microsoft YaHei UI',10))
out=Path(__file__).resolve().parent/'.runtime/wire-ui';out.mkdir(parents=True,exist_ok=True)

def wait(predicate,limit=90):
    deadline=time.monotonic()+limit
    while not predicate() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert predicate(),'Timed out waiting for audio or scene'

with TemporaryDirectory(dir=out) as folder:
    w=StudioWindow(progress_dir=Path(folder),animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    assert w._accept_case('W09');w._show_page('desk');w._activate_device('synth');app.processEvents()
    c=w.controller;errors=[]
    c.player.error.connect(errors.append);c.renderer.failed.connect(lambda r,e:errors.append(e))
    def point(widget,p):return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(widget.mapTo(w.device_proxy.widget(),p.toPoint()))))
    def click(button):
        QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(button,QPointF(button.rect().center())));app.processEvents()
    assert c.case.difficulty=='beginner' and not c.play_reference.isEnabled()
    c._prepare('target');assert c._armed is None
    click(c.example_button);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    wait(lambda:c.player.state=='stopped' and c._armed is None)
    assert c.session.attempts==0 and c.session.current==c.case.initial
    for key,target in (('h2',100),('h3',600)):
        slider=c.editor.knobs[key];option=QStyleOptionSlider();slider.initStyleOption(option)
        handle=slider.style().subControlRect(QStyle.ComplexControl.CC_Slider,option,QStyle.SubControl.SC_SliderHandle,slider)
        offset=QStyle.sliderPositionFromValue(slider.minimum(),slider.maximum(),target,slider.height()-handle.height(),option.upsideDown)
        a=QPointF(handle.center());b=QPointF(a.x(),offset+handle.height()/2)
        QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(slider,a))
        QTest.mouseMove(w.view.viewport(),pos=point(slider,b))
        QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(slider,b));app.processEvents()
    assert assess_source(c.case,c.session.current).passed,dict(c.session.current.values)
    assert c.session.attempts==0
    for _ in range(3):click(c.hint_button)
    assert c.feature_readout.isVisible()
    for lang in ('en','zh-Hant'):
        w.preferences.language=lang;w._translate();app.processEvents();w.view.grab().save(str(out/('W09-'+lang+'.png')))
    click(c.play_current);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    wait(lambda:c.player.state=='stopped' and c._armed is None)
    assert c.spectrum.traces
    click(c.submit_button);app.processEvents();assert w.page=='review' and c.session.solved
    assert load_source_session(c.save_path,c.case).solved
    w._leave_review();w._activate_device('synth');click(c.play_ab)
    wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    wait(lambda:c.player.state=='stopped' and c._armed is None)
    assert 'W09:beginner' in w.evidence_store.entries
    w.open_cabinet();panel=w.cabinet_panel
    panel.source_renderer.failed.connect(lambda r,e:errors.append(e))
    panel.selector.setCurrentIndex(panel.selector.findData('W09:beginner'));app.processEvents()
    w.view.grab().save(str(out/'W09-collected-zh-Hant.png'))
    panel.export_final();wait(lambda:bool(errors) or panel.status.text().startswith(('Exported: ','已匯出：')));assert not errors,errors
    exported=next((Path(folder)/'evidence-exports').glob('*.wav'));info=sf.info(exported)
    assert info.samplerate==44100 and info.frames==158760
    report={'scene_pointer_harmonic_faders':True,'example_without_answer_or_attempt':True,
            'bilingual_feature_readout':True,'actual_player_and_ab_completed':True,'first_clear_collection':True,
            'collected_wav_export':True,'saved_solution_reloaded':True,'sample_rate':info.samplerate,
            'frames':info.frames,'volume':0,'errors':errors,'game_root':str(GAME),'python_executable':sys.executable,
            'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe'))}
    w.close();app.processEvents();(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
