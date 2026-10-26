"""Category workshop embedded in the detective's existing equipment scene."""

from datetime import datetime
from pathlib import Path
import shutil
import uuid

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMainWindow, QProgressBar, QPushButton, QScrollArea,
    QSlider, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
    QAbstractItemView, QAbstractSpinBox)
import numpy as np

from ..audio.playback import AudioPlayer, PlaybackItem
from ..audio.source_preview import SourcePreviewRenderer
from ..audio.sound_sources import CONTROLS, SourcePatch
from ..game.sound_categories import (SourceSession, assess_source, load_source_session,
    save_source_session, source_clue)
from ..game.storage import SessionStore
from ..game.playtest import PlaytestLog
from ..game.source_learning import (DIFFICULTIES,with_difficulty,source_path,
    selected_difficulty,remember_difficulty,concept_pair,example_control)
from .edit_history import EditHistoryBar
from .hardware import PlaybackDeck, RackFace, RotaryKnob, InlineChoices
from .hover_help import set_help


class StatusLabel(QLabel):
    """Long device errors/paths must not displace the workshop controls."""
    def __init__(self):
        super().__init__()
        self.setWordWrap(True)
        self.setMaximumHeight(42)

    def setText(self,text):
        self.setToolTip(text)
        super().setText(" ".join(text.split()))


class SourcePlot(QWidget):
    """Measured traces drawn with the bundled Qt runtime; no new dependency."""
    def __init__(self):
        super().__init__()
        self.traces, self.labels = [], {}
        self.xrange, self.yrange = (0,3.6),(0,1.05)
        self.setMinimumHeight(145)

    def setXRange(self,low,high):
        self.xrange = low,high

    def setYRange(self,low,high):
        self.yrange = low,high

    def setLabel(self,axis,text,units=""):
        self.labels[axis] = text+(f" ({units})" if units else "")
        self.update()

    def clear(self):
        self.traces = []
        self.update()

    def plot(self,x,y,pen):
        self.traces.append((np.asarray(x),np.asarray(y),pen))
        self.update()

    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#18251f"))
        # Keep the final tick inside the panel and separate ticks from the title.
        area = QRectF(42,26,max(1,self.width()-84),max(1,self.height()-68))
        for i in range(5):
            p.setPen(QPen(QColor("#3c4b41"),1))
            x,y = area.left()+area.width()*i/4,area.top()+area.height()*i/4
            p.drawLine(QPointF(x,area.top()),QPointF(x,area.bottom()))
            p.drawLine(QPointF(area.left(),y),QPointF(area.right(),y))
            p.setPen(QColor("#bcb397"))
            p.drawText(QRectF(x-25,area.bottom()+2,50,17),Qt.AlignmentFlag.AlignCenter,f"{self.xrange[0]+i/4*(self.xrange[1]-self.xrange[0]):g}")
        p.drawText(8,17,self.labels.get("left",""))
        p.drawText(QRectF(42,self.height()-18,area.width(),18),Qt.AlignmentFlag.AlignCenter,self.labels.get("bottom",""))
        p.save()
        p.setClipRect(area)
        for x,y,pen in self.traces:
            path = QPainterPath()
            stride = max(1,len(x)//max(1,self.width()*2))
            for i,index in enumerate(range(0,len(x),stride)):
                point = QPointF(area.left()+(x[index]-self.xrange[0])/(self.xrange[1]-self.xrange[0])*area.width(),
                    area.bottom()-(y[index]-self.yrange[0])/(self.yrange[1]-self.yrange[0])*area.height())
                path.moveTo(point) if i == 0 else path.lineTo(point)
            p.setPen(pen);p.drawPath(path)
        p.restore()


class ChirpCurve(QWidget):
    """Drag pitch endpoints; drag the right handle horizontally for duration."""
    edited = Signal(float, float, float)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(105)
        self.setMaximumHeight(130)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.values = {"pitch": 86., "sweep": 7., "length": .18}
        self.drag = None
        self.language = "en"
        self.editable = {'pitch','sweep','length'}

    def points(self):
        v = self.values
        width, height = max(1, self.width()-70), max(1, self.height()-32)
        return (QPointF(42, 8+(106-(v["pitch"]-v["sweep"]/2))/52*height),
                QPointF(42+v["length"]/.5*width, 8+(106-(v["pitch"]+v["sweep"]/2))/52*height))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#18251f"))
        p.setPen(QPen(QColor("#425149"), 1))
        for n in (60, 72, 84, 96):
            y = 8+(106-n)/52*max(1, self.height()-32)
            p.drawLine(35, round(y), self.width()-15, round(y))
            p.setPen(QColor("#aea98c")); p.drawText(4, round(y)+4, str(n)); p.setPen(QColor("#425149"))
        start, end = self.points()
        p.setPen(QPen(QColor("#dfc17e"), 3))
        p.drawLine(start, end)
        p.setBrush(QColor("#e4cf93"))
        for point in (start, end):
            p.drawEllipse(point, 7, 7)
        p.setPen(QColor("#d6c9a7"))
        text = "拖曳兩端改音高；右端左右拖動改長度" if self.language == "zh-Hant" else "Drag ends for pitch · right end also changes length"
        p.drawText(QRectF(40,self.height()-22,self.width()-48,20), Qt.AlignmentFlag.AlignLeft, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            points = self.points()
            self.drag = min(range(2), key=lambda i: (points[i]-event.position()).manhattanLength())
            if (points[self.drag]-event.position()).manhattanLength() > 30:
                self.drag = None
                return
            self.setFocus()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag is None:
            return
        v = self.values
        start = v["pitch"]-v["sweep"]/2
        end = v["pitch"]+v["sweep"]/2
        value = 106-(event.position().y()-8)/max(1,self.height()-32)*52
        # The opposite pitch endpoint stays fixed, within recipe limits.
        other = end if self.drag == 0 else start
        value = min(other+12, 200-other, max(other-12, 120-other, value))
        if self.drag == 0:
            start = value
        else:
            end = value
        length = v["length"] if self.drag == 0 else min(.5,max(.08,(event.position().x()-42)/max(1,self.width()-70)*.5))
        pitch,sweep=(start+end)/2,end-start
        if 'sweep' not in self.editable:
            sweep=v['sweep']
            pitch=min(100,max(60,value+(sweep/2 if self.drag==0 else -sweep/2)))
        if 'pitch' not in self.editable:pitch=v['pitch']
        if 'length' not in self.editable:length=v['length']
        self.edited.emit(pitch, sweep, length)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.drag = None

    def focusOutEvent(self, event):
        self.drag = None
        super().focusOutEvent(event)


class SourceEditor(QWidget):
    changed = Signal()

    def __init__(self, patch):
        super().__init__()
        self.patch = patch
        self.controls, self.knobs, self.labels = {}, {}, {}
        self.editable = {s.key for s in CONTROLS[patch.recipe]}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.curve = ChirpCurve() if patch.recipe == "bird" else None
        if self.curve:
            layout.addWidget(self.curve)
            self.curve.edited.connect(self._curve_edit)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        face = RackFace()
        grid = QGridLayout(face)
        grid.setContentsMargins(12,8,12,8)
        grid.setSpacing(8)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        for i, spec in enumerate(CONTROLS[patch.recipe]):
            column = QWidget()
            row = QVBoxLayout(column)
            row.setContentsMargins(2,2,2,2)
            label, knob, spin = QLabel(), RotaryKnob(), QDoubleSpinBox()
            knob.setFixedSize(72,72)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            knob.setRange(0,1000)
            spin.setRange(spec.low,spec.high)
            spin.setSingleStep(spec.step)
            spin.setDecimals(3 if spec.step < .01 else 2 if spec.step < .1 else 1 if spec.step < 1 else 0)
            spin.setSuffix(spec.unit)
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setFixedWidth(122)
            spin.setFixedHeight(30)
            spin.setStyleSheet("padding: 3px 5px;")
            knob.setObjectName("source_"+spec.key+"_knob")
            spin.setObjectName("source_"+spec.key)
            row.addWidget(label)
            row.addWidget(knob,0,Qt.AlignmentFlag.AlignHCenter)
            row.addWidget(spin,0,Qt.AlignmentFlag.AlignHCenter)
            grid.addWidget(column,0,i)
            self.controls[spec.key], self.knobs[spec.key], self.labels[spec.key] = spin, knob, label
            knob.valueChanged.connect(lambda value,s=spec:self.controls[s.key].setValue(s.value_at(value/1000)))
            spin.valueChanged.connect(self._changed)
        scroll.setWidget(face)
        layout.addWidget(scroll,1)
        self.set_patch(patch)

    def _changed(self):
        self.patch = SourcePatch.make(self.patch.recipe, {k:c.value() for k,c in self.controls.items()}, self.patch.seed)
        self._sync()
        self.changed.emit()

    def _sync(self):
        for spec in CONTROLS[self.patch.recipe]:
            knob = self.knobs[spec.key]
            knob.blockSignals(True)
            knob.setValue(round(spec.position(dict(self.patch.values)[spec.key])*1000))
            knob.blockSignals(False)
        if self.curve:
            self.curve.values = dict(self.patch.values)
            self.curve.update()

    def _curve_edit(self,pitch,sweep,length):
        values = dict(self.patch.values)
        values.update({key:value for key,value in dict(pitch=round(pitch,1),sweep=round(sweep,1),length=round(length,3)).items() if key in self.editable})
        self.set_patch(SourcePatch.make("bird",values,self.patch.seed))
        self.changed.emit()

    def set_patch(self, patch):
        self.patch = patch
        for key,value in patch.values:
            control = self.controls[key]
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        self._sync()

    def translate(self,language):
        zh = language == "zh-Hant"
        for spec in CONTROLS[self.patch.recipe]:
            self.labels[spec.key].setText(spec.labels[zh])
            for widget in (self.labels[spec.key],self.controls[spec.key],self.knobs[spec.key]):
                widget.setToolTip(spec.help[zh]+('' if spec.key in self.editable else (' 此難度已代為設定，無需調整。' if zh else ' Already set for this difficulty; no adjustment is needed.')))
        if self.curve:
            self.curve.language = language
            self.curve.setToolTip("上下拖曳端點改變音高；左右拖動右端點改變鳥鳴長度。" if zh else
                "Drag endpoints vertically to change pitch; drag the right endpoint horizontally to change chirp length.")
            self.curve.update()


    def set_editable(self,keys):
        self.editable=set(keys)
        for key in self.controls:
            self.controls[key].setEnabled(key in self.editable)
            self.knobs[key].setEnabled(key in self.editable)
        if self.curve:self.curve.editable=self.editable


class SourceCaseWindow(QMainWindow):
    case_completed = Signal()
    difficulty_changing = Signal()
    difficulty_changed = Signal()
    device_requested = Signal(str)

    def __init__(self, *, case, save_path, language="en", volume=.35, embedded=True, renderer=None, player=None,difficulty='advanced'):
        super().__init__()
        self.base_case,self.base_save_path=case,Path(save_path)
        difficulty=selected_difficulty(save_path) if difficulty is None else difficulty
        self.case, self.save_path, self.embedded = with_difficulty(case,difficulty),source_path(save_path,difficulty),embedded
        self._language, self._closed, self._save_blocked = language, False, False
        self._revision, self._armed, self._warning = -1, None, ""
        self.playtest_log=None;self._recording=False
        self.device_kind = "synth"
        try:
            self.session = load_source_session(self.save_path,self.case)
        except (OSError,ValueError,TypeError,KeyError):
            try:
                SessionStore(self.save_path).preserve_invalid()
                self._warning = "backup"
            except OSError:
                self._save_blocked = True
                self._warning = "blocked"
            self.session = SourceSession(self.case)
        self.update_timer=QTimer(self);self.update_timer.setSingleShot(True);self.update_timer.setInterval(400)
        self.update_timer.timeout.connect(lambda:self._prepare('loop') if self.loop_button.isChecked() else None)
        self.renderer = renderer or SourcePreviewRenderer(self)
        self.player = player or AudioPlayer(self)
        self.renderer.ready.connect(self._ready)
        self.renderer.failed.connect(self._failed)
        self.player.error.connect(lambda msg:self.status.setText(msg))
        self.player.state_changed.connect(self._player_state)
        self.language = QComboBox()
        self.language.addItem("English","en")
        self.language.addItem("繁體中文","zh-Hant")
        self.language.setCurrentIndex(language == "zh-Hant")
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0,100)
        self.volume.setValue(round(volume*100))
        self.volume.valueChanged.connect(lambda value:self.player.set_volume(value/100))
        self.player.set_volume(volume)
        self._build()
        self.language.currentIndexChanged.connect(self._language_changed)
        self.edit_bar = EditHistoryBar(self,self.session.current,self._restore_edit)
        self.editor.set_editable(self.case.editable_parameters)
        self._translate()

    @property
    def zh(self):
        return self._language == "zh-Hant"

    def text(self,en,zh):
        return zh if self.zh else en

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10,8,10,8)
        layout.setSpacing(6)
        header = QHBoxLayout()
        self.title = QLabel()
        header.addWidget(self.title,1)
        self.difficulty=InlineChoices(columns=3)
        for key in DIFFICULTIES:self.difficulty.addItem(key,key)
        self.difficulty.setCurrentIndex(self.difficulty.findData(self.case.difficulty))
        self.difficulty.currentIndexChanged.connect(self._change_difficulty)
        header.addWidget(self.difficulty)
        header.addWidget(self.language)
        header.addWidget(self.volume)
        layout.addLayout(header)
        if self.embedded:
            self.language.hide(); self.volume.hide()
        columns = QHBoxLayout()
        self.notebook = QGroupBox()
        self.notebook.setMaximumWidth(345)
        left = QVBoxLayout(self.notebook)
        notes = QWidget()
        notes_layout = QVBoxLayout(notes)
        notes_layout.setContentsMargins(2,2,2,2)
        self.story, self.score, self.feedback, self.review = [QLabel() for _ in range(4)]
        for label in (self.story,self.score,self.feedback):
            label.setWordWrap(True)
            notes_layout.addWidget(label)
        notes_layout.addStretch()
        self.note_scroll = QScrollArea()
        self.note_scroll.setWidgetResizable(True)
        self.note_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.note_scroll.setMinimumHeight(0)
        self.note_scroll.setWidget(notes)
        left.addWidget(self.note_scroll,1)
        self.score.setStyleSheet("font-size: 18px; color: #ecd091;")
        self.review.hide()
        self.hint_button = QPushButton()
        self.hint_button.clicked.connect(self._hint)
        left.addWidget(self.hint_button)
        self.example_button=QPushButton()
        self.example_button.clicked.connect(lambda:self._prepare('example'))
        self.play_reference, self.play_current, self.stop_button, self.play_ab = [QPushButton() for _ in range(4)]
        self.play_current.clicked.connect(lambda:self._prepare("current"))
        self.play_reference.clicked.connect(lambda:self._prepare("target"))
        self.play_ab.clicked.connect(lambda:self._prepare("ab"))
        self.stop_button.clicked.connect(self.stop)
        self.deck = PlaybackDeck(self.play_reference,self.play_current,self.stop_button,self.play_ab,compact=True)
        self.player.state_changed.connect(self.deck.set_state)
        left.addWidget(self.deck)
        self.loop_button=QPushButton();self.loop_button.setCheckable(True)
        self.loop_button.toggled.connect(lambda enabled:self._prepare('loop') if enabled else self.stop())
        columns.addWidget(self.notebook,3)
        self.workbench = QGroupBox()
        right = QVBoxLayout(self.workbench)
        nav = QHBoxLayout()
        self.source_button, self.analysis_button = QPushButton(),QPushButton()
        self.source_button.clicked.connect(lambda:self.device_requested.emit("synth"))
        self.analysis_button.clicked.connect(lambda:self.device_requested.emit("analyzer"))
        nav.addWidget(self.source_button); nav.addWidget(self.analysis_button)
        nav.addWidget(self.example_button);nav.addWidget(self.loop_button)
        right.addLayout(nav)
        self.editor = SourceEditor(self.session.current)
        self.editor.changed.connect(self._changed)
        right.addWidget(self.editor,1)
        self.unused = QLabel()
        self.unused.setWordWrap(True)
        right.addWidget(self.unused)
        self.analysis = QWidget()
        graphs = QVBoxLayout(self.analysis)
        graphs.setContentsMargins(0,0,0,0)
        self.analysis_note = QLabel()
        self.analysis_note.setWordWrap(True)
        graphs.addWidget(self.analysis_note)
        self.plots = QTabWidget()
        self.spectrum, self.envelope = SourcePlot(),SourcePlot()
        self.plots.addTab(self.spectrum,"")
        self.plots.addTab(self.envelope,"")
        self.spectrum.setXRange(0,10000)
        self.spectrum.setYRange(-75,0)
        self.envelope.setYRange(0,1.05)
        graphs.addWidget(self.plots,1)
        self.history = QTableWidget(0,3)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.verticalHeader().hide()
        versions = QWidget()
        versions_layout = QVBoxLayout(versions)
        versions_layout.setContentsMargins(0,0,0,0)
        versions_layout.addWidget(self.history,1)
        self.restore_button = QPushButton()
        self.restore_button.clicked.connect(self._restore_record)
        versions_layout.addWidget(self.restore_button)
        self.plots.addTab(versions,"")
        study=QWidget();study_layout=QVBoxLayout(study)
        self.playtest_note=QLabel();self.playtest_note.setWordWrap(True)
        self.record_button=QPushButton();self.record_button.setCheckable(True)
        self.record_button.toggled.connect(self._record_toggled)
        self.log_export_button=QPushButton();self.log_export_button.clicked.connect(self._export_log)
        study_layout.addWidget(self.playtest_note);study_layout.addWidget(self.record_button)
        study_layout.addWidget(self.log_export_button);study_layout.addStretch()
        self.plots.addTab(study,'')
        right.addWidget(self.analysis,1)
        columns.addWidget(self.workbench,7)
        layout.addLayout(columns,1)
        actions = QHBoxLayout()
        self.submit_button,self.reset_button,self.export_button = QPushButton(),QPushButton(),QPushButton()
        self.submit_button.setObjectName("source_submit")
        self.submit_button.clicked.connect(self._submit)
        self.reset_button.clicked.connect(lambda:self._restore_edit(self.case.initial,record=True))
        self.export_button.clicked.connect(lambda:self._prepare("export"))
        for button in (self.submit_button,self.reset_button,self.export_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.busy = QProgressBar()
        self.busy.setRange(0,0); self.busy.setFixedHeight(3); self.busy.hide()
        layout.addWidget(self.busy)
        self.status,self.save_warning = StatusLabel(),StatusLabel()
        layout.addWidget(self.status); layout.addWidget(self.save_warning)
        self.shortcut = QShortcut(QKeySequence("Escape"),self)
        self.shortcut.activated.connect(self.stop)
        self.shortcut.setEnabled(not self.embedded)
        self.resize(1180,690)

    def _language_changed(self,index):
        self._language = self.language.itemData(index)
        self._translate()

    def _change_difficulty(self,index):
        key=self.difficulty.itemData(index)
        if key==self.case.difficulty:return
        self.difficulty_changing.emit();self.stop();self._save()
        self.case=with_difficulty(self.base_case,key)
        self.save_path=source_path(self.base_save_path,key)
        self._warning='';self._save_blocked=False
        try:self.session=load_source_session(self.save_path,self.case)
        except (OSError,ValueError,TypeError,KeyError):
            try:SessionStore(self.save_path).preserve_invalid();self._warning='backup'
            except OSError:self._warning='blocked';self._save_blocked=True
            self.session=SourceSession(self.case)
        self.editor.set_patch(self.session.current);self.editor.set_editable(self.case.editable_parameters)
        self.edit_bar.reset(self.session.current)
        self.spectrum.clear();self.envelope.clear()
        try:remember_difficulty(self.base_save_path,key)
        except OSError:self._warning='blocked'
        self._translate();self._save();self._record('difficulty');self.difficulty_changed.emit()

    def _record_toggled(self,enabled):
        if enabled:
            self.playtest_log=PlaytestLog(self.base_save_path.parent/'playtests')
            self._recording=True;self._record('start')
        else:
            self._record('end');self._recording=False

    def _record(self,event,**values):
        if not self._recording or self.playtest_log is None:return
        try:self.playtest_log.record(self.case,event,attempts=self.session.attempts,**values)
        except (OSError,ValueError) as error:
            self._recording=False
            self.record_button.blockSignals(True);self.record_button.setChecked(False);self.record_button.blockSignals(False)
            self.status.setText(self.text('Recording stopped: ','記錄已停止：')+str(error))

    def _export_log(self):
        try:
            if self.playtest_log is None:raise ValueError(self.text('Enable playtest recording first.','請先啟用試玩記錄。'))
            self.status.setText(self.text('Exported: ','已匯出：')+str(self.playtest_log.export_csv()))
        except (OSError,ValueError) as error:self.status.setText(str(error))

    def _translate(self):
        self.title.setText(f"{self.case.id} · {self.case.title[self._language]}")
        self.setWindowTitle(self.title.text())
        self.notebook.setTitle(self.text("Witness notebook","證人口供"))
        self.workbench.setTitle(self.text("Sound construction workshop","聲音合成工作台"))
        self.story.setText(self.case.story[self._language])
        for key,button in zip(DIFFICULTIES,self.difficulty.buttons):
            button.setText(DIFFICULTIES[key][self.zh])
            set_help(button,'source_difficulty',self._language)
        captions = (
            (self.hint_button,"More help · free","再給我一點幫助 · 免費","hint"),
            (self.example_button,"Hear example","聽控制示例","source_example"),
            (self.loop_button,"Loop mine · auto update","循環我的聲音 · 自動更新","source_loop"),
            (self.play_current,"Play my sound","試聽我的聲音","play_current"),
            (self.play_ab,"A/B · target → mine","A/B · 目標 → 我的聲音","play_ab"),
            (self.stop_button,"Stop · Esc","停止 · Esc","stop"),
            (self.source_button,"Sound sources","聲源設備","source_workshop"),
            (self.analysis_button,"Analysis / versions","分析與版本","source_analysis"),
            (self.submit_button,"Submit construction","提交合成版本","source_submit"),
            (self.reset_button,"Reset sound","重設聲音","source_reset"),
            (self.export_button,"Export my WAV","匯出我的 WAV","source_export"),
            (self.restore_button,"Restore selected version","恢復選中版本","source_restore"))
        for button,en,zh,key in captions:
            button.setText(self.text(en,zh)); set_help(button,key,self._language)
        self.editor.translate(self._language)
        self.deck.translate(self._language)
        self.plots.setTabText(0,self.text("Spectrum","頻譜"))
        self.plots.setTabText(1,self.text("Amplitude envelope","振幅包絡"))
        self.plots.setTabText(2,self.text("Versions","版本記錄"))
        self.plots.setTabText(3,self.text('Playtest log','試玩記錄'))
        self.playtest_note.setText(self.text('Optional local observation log: anonymous ID, elapsed time, difficulty, edits, hints, examples and all submissions. Recording is off by default. Logs are not a controlled study or evidence of learning effectiveness.','可選的本機觀察記錄：匿名代碼、時間、難度、調參、提示、示例和所有提交。預設關閉；記錄本身不是受控實驗或學習成效證據。'))
        for button,en,zh,key in ((self.record_button,'Record this playtest','記錄這次試玩','playtest_record'),(self.log_export_button,'Export events · CSV','匯出事件 · CSV','playtest_export')):
            button.setText(self.text(en,zh));set_help(button,key,self._language)
        self.spectrum.setLabel("bottom",self.text("Frequency","頻率"),units="Hz")
        self.spectrum.setLabel("left",self.text("Relative power","相對能量"),units="dB")
        self.envelope.setLabel("bottom",self.text("Time","時間"),units="s")
        self.envelope.setLabel("left",self.text("Normalized RMS","正規化 RMS"))
        set_help(self.plots,"source_graphs",self._language)
        set_help(self.history,"source_history",self._language)
        set_help(self.language,"language",self._language);set_help(self.volume,"volume",self._language)
        if hasattr(self,"edit_bar"):
            self.edit_bar.translate(self._language)
        self.status.setText(self.text("Build from the witness clues. Unlimited submissions; hints are free.","依照口供製作聲音。不限提交次數，提示免費。"))
        self._refresh()

    def _refresh(self):
        s = self.session
        if s.last:
            result = assess_source(self.case,s.last)
            suffix = self.text(" · edited since submission"," · 提交後已修改") if s.current != s.last else ""
            self.score.setText(self.text(f"Construction {result.total:.1f} / 100 · #{s.attempts}",f"合成進度 {result.total:.1f} / 100 · 第 {s.attempts} 次")+suffix)
        else:
            self.score.setText(self.text("No submission yet","尚未提交"))
        clue = source_clue(self.case,s.current,s.hints,self._language) if s.hints else self.text(
            "Shape the sound described above. Ask for a clue to find the largest remaining difference.","先製作口供描述的聲音；領取提示可找出目前最大的差異。")
        self.feedback.setText(self.text("Reconstructed! Target unlocked.\n","合成完成！目標已解鎖。\n")+clue if s.solved else clue)
        self.review.hide()
        if s.solved:
            self.review.setText(self.text("Reference settings: ","參考設定：")+" · ".join(
                f"{spec.labels[self.zh]} {dict(self.case.target.values)[spec.key]:g}" for spec in CONTROLS[s.current.recipe]))
        self.play_reference.setText(self.text("Play target","播放目標") if s.solved else self.text("Target · hidden","目標 · 未揭曉"))
        self.play_reference.setEnabled(s.solved); self.play_ab.setEnabled(s.solved)
        set_help(self.play_reference,"hidden_target",self._language)
        self.hint_button.setText(self.text(f"More help · free ({s.hints}/3)",f"再給我一點幫助 · 免費（{s.hints}/3）"))
        self.history.setHorizontalHeaderLabels(self.text(("Version","Progress","Result"),("版本","進度","結果")))
        self.history.setRowCount(len(s.records))
        for i,record in enumerate(s.records):
            result = assess_source(self.case,SourcePatch.from_dict(record["patch"]))
            for j,value in enumerate((str(record["number"]),f"{result.total:.1f}",self.text("Passed","通過") if result.passed else self.text("Investigating","調查中"))):
                self.history.setItem(i,j,QTableWidgetItem(value))
        self.restore_button.setEnabled(bool(s.records))
        if self._warning:
            self.save_warning.setText(self.text("Unreadable progress backed up; a fresh case has started.","無法讀取的進度已備份，目前開始新案件。") if self._warning == "backup" else self.text("Could not save progress. The original file is retained.","無法儲存進度，原檔已保留。"))
        self.save_warning.setVisible(bool(self._warning))
        self.present_device(self.device_kind)

    def present_device(self,device):
        self.device_kind = device
        self.editor.setVisible(device == "synth")
        self.analysis.setVisible(device == "analyzer")
        self.unused.setVisible(device not in ("synth","analyzer","tape"))
        self.unused.setText(self.text("This case uses the sound-source synthesizer. Open Sound sources to adjust it; extra Delay and Reverb are not used.","本案件使用聲源合成器。點「聲源設備」即可調整；此關不使用額外 Delay 或 Reverb。"))
        self.analysis_note.setText(self.text("Play your sound to update these measurements. Gold: yours; green: target (after solving). Scores use accepted sound-attribute bands, not waveform similarity.","試聽後更新實測圖表。金色：你的聲音；綠色：目標（通關後）。進度依聲音特徵的可接受範圍計算，不是波形相似度。"))
        if self.session.solved:
            self.analysis_note.setText(self.analysis_note.text()+"\n"+self.review.text())

    def _changed(self):
        looping=self.loop_button.isChecked()
        self.stop(keep_loop=looping)
        self.session.update(self.editor.patch)
        self.edit_bar.record(self.session.current)
        self.spectrum.clear();self.envelope.clear()
        self._refresh();self._save()
        self._record('edit')
        if looping:self.update_timer.start()

    def _restore_edit(self,patch,*,record=False):
        looping=self.loop_button.isChecked()
        self.stop(keep_loop=looping)
        self.session.update(patch)
        self.editor.set_patch(patch)
        if record:
            self.edit_bar.record(patch,merge=False)
        self.spectrum.clear();self.envelope.clear()
        self._refresh();self._save()
        self._record('edit')
        if looping:self.update_timer.start()

    def _restore_record(self):
        row = self.history.currentRow()
        if row >= 0:
            self._restore_edit(SourcePatch.from_dict(self.session.records[row]["patch"]),record=True)

    def _submit(self):
        was_solved = self.session.solved
        self.stop()
        result = self.session.submit()
        self._record('submit',score=result.total)
        self._refresh();self._save()
        if not was_solved and self.session.solved:
            self.case_completed.emit()
        parts = " · ".join(f"{spec.labels[self.zh]} {result.scores[spec.key]:.0f}" for spec in CONTROLS[self.session.current.recipe] if spec.key in result.scores)
        self.status.setText(self.text("Passed! ","通關！")+parts if result.passed else
            self.text("Goal: 90 overall and 85 per attribute. ","目標：總分 90，各項至少 85。")+parts)
        QTimer.singleShot(0,lambda:self.note_scroll.ensureWidgetVisible(self.score) if not self._closed else None)

    def _hint(self):
        self.session.hints = min(3,self.session.hints+1)
        self._refresh();self._save()
        self._record('hint')
        QTimer.singleShot(0,lambda:self.note_scroll.ensureWidgetVisible(self.feedback) if not self._closed else None)

    def _prepare(self,mode):
        if self._closed or mode in ("target","ab") and not self.session.solved:
            return
        if mode=='current' and self.loop_button.isChecked():mode='loop'
        self.stop(keep_loop=mode=='loop')
        requests = {"target":self.case.target,"current":self.session.current} if mode == "ab" else {
            "target" if mode == "target" else "current":self.case.target if mode == "target" else self.session.current}
        if mode=='example':
            self._example_key=example_control(self.case,self.session.current)
            low,high=concept_pair(self.case.target.recipe,self._example_key)
            requests={'low':low,'high':high}
            self._record('example',control=self._example_key)
        elif mode=='loop':self._record('loop')
        self._armed = mode,tuple(requests)
        self.busy.show()
        self.status.setText(self.text("Preparing procedural audio…","正在合成聲音……"))
        try:
            self._revision = self.renderer.prepare(requests)
        except (OSError,ValueError,RuntimeError) as error:
            self._failed(self._revision,str(error))

    def _ready(self,revision,previews):
        if self._closed or revision != self._revision or self._armed is None:
            return
        mode,keys = self._armed
        self._armed = None
        self.busy.hide()
        self.spectrum.clear();self.envelope.clear()
        try:
            for key in keys:
                measurements = previews[key].measurements
                if mode=='example':continue
                pen = QPen(QColor("#9cb9a0" if key == "target" else "#e5c37a"),1.4)
                self.spectrum.plot(measurements["spectrum_hz"],measurements["spectrum_db"],pen=pen)
                self.envelope.plot(measurements["envelope_seconds"],measurements["envelope"],pen=pen)
            if mode == "export":
                folder = self.save_path.parent/"exports"
                folder.mkdir(parents=True,exist_ok=True)
                path = folder/f"{self.case.id}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.wav"
                shutil.copyfile(previews["current"].listening_path,path)
                self.status.setText(self.text("Exported: ","已匯出：")+str(path))
            else:
                if mode=='example':
                    spec=next(s for s in CONTROLS[self.case.target.recipe] if s.key==self._example_key)
                    self.player.play([PlaybackItem(previews[key].listening_path,self.text('Lower ','較低的')+spec.labels[self.zh] if key=='low' else self.text('Higher ','較高的')+spec.labels[self.zh]) for key in keys])
                    self.status.setText(self.text('Example only: lower → higher. ','僅為教學示例：較低 → 較高。')+spec.help[self.zh])
                else:
                    self.player.play([PlaybackItem(previews[key].listening_path,self.text("Target","目標") if key == "target" else self.text("My sound","我的聲音"),loop=mode=='loop') for key in keys])
                    self.status.setText(self.text("Playing. Open Analysis & versions for measured spectrum and envelope.","正在播放；點「分析與版本」可查看實測頻譜和包絡。"))
        except (OSError,ValueError,RuntimeError,KeyError) as error:
            self._failed(self._revision,str(error))

    def _failed(self,revision,message):
        if not self._closed and revision == self._revision:
            self._armed = None;self.busy.hide()
            self.loop_button.blockSignals(True);self.loop_button.setChecked(False);self.loop_button.blockSignals(False)
            self.update_timer.stop()
            self.status.setText(self.text("Audio error: ","音訊錯誤：")+message)

    def _player_state(self,state,label):
        if self._closed or not hasattr(self,"status"):
            return
        if state=='error':self.stop();return
        if state in ("loading","playing"):
            self.status.setText(self.text("Playing: ","正在播放：")+label)
        elif state == "stopped" and self._armed is None and self.status.text().startswith(("Playing", "正在播放")):
            self.status.setText(self.text("Stopped.","已停止。"))

    def stop(self,*,keep_loop=False):
        self.update_timer.stop()
        if not keep_loop:
            self.loop_button.blockSignals(True);self.loop_button.setChecked(False);self.loop_button.blockSignals(False)
        self._armed = None
        self.renderer.cancel()
        self._revision = self.renderer.revision
        self.player.stop()
        self.busy.hide()
        self.status.setText(self.text("Stopped.","已停止。"))

    def _save(self):
        if not self._save_blocked:
            try:
                save_source_session(self.save_path,self.session)
            except (OSError,ValueError):
                self._warning = "blocked"
                self.save_warning.setText(self.text("Progress could not be saved; the original is retained.","無法儲存進度，原檔已保留。"));self.save_warning.show()

    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowDeactivate and hasattr(self,"player") and not self.embedded:
            QTimer.singleShot(0,lambda:self.stop() if not self._closed and not self.isActiveWindow() else None)

    def closeEvent(self,event):
        if not self._closed:
            self._record('end');self._recording=False
            self.stop();self._save();self._closed = True
            self.player.close();self.renderer.close()
        event.accept()
