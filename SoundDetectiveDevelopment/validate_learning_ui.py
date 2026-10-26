"""Muted real-SC/Qt integration, using disposable saves and scene pointer input."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(os.environ.get('SOUND_DETECTIVE_QA_GAME',str(Path(__file__).resolve().parents[1]/'SoundDetective'))).resolve()
sys.path.insert(0,str(GAME))
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import soundfile as sf
from sound_detective.ui.studio import StudioWindow
from sound_detective.audio.sc_client import find_executable

app=QApplication([])
for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Microsoft YaHei UI',10))
out=Path(__file__).resolve().parent/'.runtime/learning-ui';out.mkdir(parents=True,exist_ok=True)

def wait(predicate,limit=60):
    until=time.monotonic()+limit
    while not predicate() and time.monotonic()<until:app.processEvents();time.sleep(.01)
    assert predicate(),'UI/audio timed out'

with TemporaryDirectory(dir=out) as folder:
    w=StudioWindow(progress_dir=Path(folder),animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    assert w._accept_case('W04');w._show_page('desk');w._activate_device('synth');app.processEvents()
    c=w.controller;errors=[];prepared=[]
    c.player.error.connect(errors.append);c.renderer.failed.connect(lambda r,e:errors.append(e))
    original=c.renderer.prepare
    def prepare(requests):
        prepared.append(requests);return original(requests)
    c.renderer.prepare=prepare

    def click(button):
        root=w.device_proxy.widget()
        point=w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(button.mapTo(root,button.rect().center()))))
        QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point);app.processEvents()

    click(c.difficulty.buttons[1]);assert c.case.difficulty=='standard'
    click(c.difficulty.buttons[0]);assert c.case.difficulty=='beginner'
    curve=c.editor.curve;root=w.device_proxy.widget()
    def mapped(point):return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(curve.mapTo(root,point.toPoint()))))
    start=curve.points()[1];end=start+QPointF(-40,-10)
    QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=mapped(start))
    QTest.mouseMove(w.view.viewport(),pos=mapped(end))
    QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=mapped(end));app.processEvents()
    assert dict(c.session.current.values)['sweep']==dict(c.case.target.values)['sweep']
    w.view.grab().save(str(out/'workshop-en.png'))
    c.loop_button.click();wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    count=len(prepared);c.editor.controls['pitch'].setValue(81)
    wait(lambda:bool(errors) or len(prepared)>count and c._armed is None and c.player.state=='playing')
    assert not errors,errors
    assert dict(prepared[-1]['current'].values)['pitch']==81
    c._prepare('example');wait(lambda:bool(errors) or c._armed is None and c.player.state=='playing')
    assert not errors,errors
    wait(lambda:c.player.state=='stopped');assert c.session.attempts==0
    c._restore_edit(c.case.target,record=True);c._submit();app.processEvents()
    assert w.page=='review'
    w._leave_review();w.open_cabinet();app.processEvents()
    assert w.cabinet_panel.selector.count()==1
    w.view.grab().save(str(out/'cabinet-en.png'))
    w.cabinet_panel.player.error.connect(errors.append)
    w.cabinet_panel.source_renderer.failed.connect(lambda r,e:errors.append(e))
    w.cabinet_panel.export_final()
    wait(lambda:bool(errors) or w.cabinet_panel.status.text().startswith('Exported: '))
    assert not errors,errors
    exported=list((Path(folder)/'evidence-exports').glob('*.wav'));assert len(exported)==1
    audio,rate=sf.read(exported[0]);assert rate==44100 and len(audio)==158760
    w.preferences.language='zh-Hant';w._translate();app.processEvents()
    w.view.grab().save(str(out/'cabinet-zh-Hant.png'))
    w.go_back();w.preferences.language='zh-Hant';w._translate();app.processEvents()
    w.view.grab().save(str(out/'workshop-zh-Hant.png'))
    c.present_device('analyzer');c.plots.setCurrentIndex(3);app.processEvents()
    w.view.grab().save(str(out/'playtest-zh-Hant.png'))
    c.record_button.click();c._submit();c.record_button.click();c._export_log()
    assert list((Path(folder)/'wordle/playtests').glob('*.csv'))
    w.close();app.processEvents()
    report={'real_scene_difficulty_clicks':True,'locked_chirp_gesture':True,
            'real_loop_and_latest_edit':True,'example_completed_without_submission':True,
            'collection_render_and_export':True,'export_frames':len(audio),'sample_rate':rate,
            'anonymous_csv_export':True,'speaker_volume':0,'errors':errors,
            'game_root':str(GAME),'python_executable':sys.executable,
            'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe'))}
    (out/'result.json').write_text(json.dumps(report,indent=2),'utf-8')
    print(json.dumps(report),flush=True)
