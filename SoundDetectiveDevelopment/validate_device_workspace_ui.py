"""Physical tape controls and enlarged device workspace in the actual scene."""
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
from sound_detective.game.availability import music_availability
from sound_detective.audio.sc_client import find_executable

app=QApplication([])
for name in ('segoeui.ttf','msyh.ttc','msjh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Microsoft JhengHei UI',10))
out=Path(os.environ.get('SOUND_DETECTIVE_QA_OUTPUT',str(Path(__file__).resolve().parent/'.runtime/device-workspace-ui'))).resolve()
out.mkdir(parents=True,exist_ok=True)

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
    c=activate('T01');screenshot('T01')
    if '--layout-only' not in sys.argv:
        click(c.deck.reference_display);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
        click(c.deck.display);wait(lambda:bool(errors) or c.player.state=='playing' and not c.deck.reference_display.playing);assert not errors,errors
        click(c.deck.stop);wait(lambda:c.player.state=='stopped')
        click(c.compare_button);wait(lambda:bool(errors) or c.session.attempt_count==1 and c._submission_token is None);assert not errors,errors
    c=activate('T09','delay');screenshot('T09')
    c=activate('W01');screenshot('W01')
    c=activate('W02');screenshot('W02')
    assert not c.tempo_panel.isVisible() and not any(b.isVisible() for b in c.mode_buttons.values())
    c=activate('W09');screenshot('W09')
    if '--layout-only' not in sys.argv:
        before=c.session.hints;click(c.hint_button);assert c.session.hints==min(3,before+1) and c.device_kind=='synth'
        click(c.deck.display);wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
        click(c.deck.stop);wait(lambda:c.player.state=='stopped')
    music=music_availability().available
    if music:
        c=activate('M01');before=c.session.settings
        click(c.check_repair_button)
        assert c.device_kind=='synth' and c.session.stage=='filter' and c.session.settings==before
        screenshot('M01')
    assert w.open_free_composition();w._show_page('desk');w._activate_device('synth');app.processEvents();c=w.controller
    assert c.tempo_panel.isVisible() and not c.deck.reference_frame.isVisible()
    c.tempo.setValue(126);assert c.session.current.tempo==126
    screenshot('FREE')
    report={'volume':0,'game_root':str(GAME),'python_executable':sys.executable,'optional_music_checked':music,
        'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe')),
        'layout_only':'--layout-only' in sys.argv,'errors':errors}
    assert not errors,errors
    w.close();app.processEvents();(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
