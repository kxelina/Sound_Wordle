"""W02 and an independent free-composition draft, sharing the SC renderer."""

from pathlib import Path
import math

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QProgressBar, QPushButton, QSlider, QSpinBox,
    QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,QFrame)

from ..audio.playback import AudioPlayer, PlaybackItem
from ..audio.preview import PreviewRenderer
from ..audio.sc_client import ROOT
from ..game.melody import (Draft, MelodyCase, MelodySession, LOW_PITCH, TEMPO,
    compare_draft, load_melody_session, save_melody_session, teaching_pair,authored_melody_clue)
from ..game.progress import PROGRESS_CLUES
from ..game.storage import SessionStore
from .hardware import PlaybackDeck
from .parameter_editor import ParameterEditor
from .investigation_feedback import SubmissionFeedback,ScoreSnapshot,guidance,progress_control,device_for
from .piano_roll import PianoRollEditor


TEXT = {
    "en": {
        "title": "Sound Detective · W02 · Melody Workshop",
        "modes": ("W02 challenge", "Free composition"),
        "rules": "One bar · 16 cells · C4–C5 · unlimited submissions · free clues. Target playback unlocks after success.",
        "free_rules": "Free composition · no grading. Your free draft and challenge progress are saved separately.",
        "story": "Four notes, one on each beat. It climbs twice, then steps down. The last note lasts longer; the tone is bright and short, with a gentle echo.",
        "stages": ("1 · Rhythm", "2 · Melody", "3 · Timbre"),
        "groups": ("Rhythm", "Melody", "Timbre"), "free": "Your composition",
        "free_notebook": "Composition notes", "free_machine": "Free composition",
        "score": "Submission {n} · progress {score} / 100", "unscored": "Not submitted · unlimited attempts",
        "stale": "Edited since submission; the scores belong to the previous version.",
        "tabs": ("Piano roll", "Synthesizer"), "notebook": "Witness notebook",
        "devices": ("Workshop", "Filter", "Delay", "Reverb", "History"),
        "submit": "Submit version", "hint": "More help (free)", "lesson": "Hear the concept",
        "next": "Suggested device", "reset": "Reset this draft", "history": "Submission history",
        "restore": "Restore", "hear": "Hear selected", "columns": ("Version", "Rhythm", "Melody", "Timbre"),
        "current": "Play my melody", "target": "Target · hidden", "target_open": "Play target",
        "ab": "A/B · target → mine", "stop": "Stop · Esc", "tempo": "BPM",
        "locked": "First submit a passing rhythm, then a passing melody, to unlock sound controls.",
        "pitch_locked": "Rhythm stage: pitch stays at C4. Submit to unlock pitch editing.",
        "initial": "Click the piano roll to add notes, then listen. Hints can reveal rhythm marks and partial notes.",
        "hidden": "Complete all three stages before hearing the target.",
        "generating": "Preparing audio…", "playing": "Playing: {label}", "stopped": "Stopped.",
        "empty": "Add at least one note with an audible harmonic before playing or submitting.",
        "submitted": "Progress recorded. Scores describe reconstruction progress, not perceptual similarity.",
        "solved": "Message reconstructed! Target playback and A/B are unlocked.",
        "practice": "Practice · the target has already been revealed.",
        "ready": "This stage is ready. Submit to record it and unlock the next stage.",
        "free_help": "Choose any pitches and rhythm. All sound controls are available; no score or attempt penalty.",
        "lesson_note": "Generic teaching pair; this is not the hidden target.",
        "error": "Audio error: {message}", "saved_bad": "Unreadable W02 progress backed up; starting a new draft.",
        "save_error": "Could not save W02; the original file has been retained.",
        "tier": "Help {n}/3 · {text}",
    },
    "zh-Hant": {
        "title": "Sound Detective · W02 · 旋律工作台",
        "modes": ("W02 挑戰", "自由創作"),
        "rules": "一小節 · 16 格 · C4–C5 · 不限提交 · 免費提示；通關後揭曉目標。",
        "free_rules": "自由創作 · 不評分；創作草稿與挑戰進度分開儲存。",
        "story": "四個音，每拍響一次。先向上兩次，再向下。最後一音較長；音色明亮短促，帶輕微回聲。",
        "stages": ("1 · 節奏", "2 · 旋律", "3 · 音色"),
        "groups": ("節奏", "旋律", "音色"), "free": "你的創作草稿",
        "free_notebook": "創作筆記", "free_machine": "自由創作",
        "score": "第 {n} 次提交 · 重建進度 {score} / 100", "unscored": "尚未提交 · 次數不限",
        "stale": "已修改；以上分數屬於上次提交。", "tabs": ("鋼琴卷簾", "合成器"),
        "notebook": "證人口供", "devices": ("工作台", "濾波", "回聲", "混響", "記錄"),
        "submit": "提交目前版本", "hint": "再給我幫助（免費）", "lesson": "聽聽概念",
        "next": "建議設備", "reset": "重設目前草稿", "history": "提交記錄", "restore": "恢復版本",
        "hear": "試聽選中版本", "columns": ("版本", "節奏", "旋律", "音色"),
        "current": "播放我的旋律", "target": "目標 · 未揭曉", "target_open": "播放目標",
        "ab": "A/B · 目標 → 我的", "stop": "停止 · Esc", "tempo": "BPM",
        "locked": "先提交達標的節奏，再完成旋律，便會開放音色與效果控制。",
        "pitch_locked": "節奏階段固定 C4；提交達標後開放音高。",
        "initial": "點擊卷簾加音，再試聽；提示可逐步顯示節奏標記與部分音符。",
        "hidden": "三階段均達標後才可播放目標。", "generating": "正在準備音訊……",
        "playing": "正在播放：{label}", "stopped": "已停止。",
        "empty": "請先加入至少一個音符，並保留可發聲的諧波，再播放或提交。",
        "submitted": "已記錄重建進度；這不是人耳相似度百分比。",
        "solved": "留言重建完成！已解鎖目標試聽與 A/B。", "practice": "練習 · 目標已曾揭曉。",
        "ready": "這部分已達標，提交後記錄成果並開放下一階段。",
        "free_help": "音高、節奏自由編排；全部音色控制已開放，不評分、不計次。",
        "lesson_note": "一般教學對比，並非隱藏的目標旋律。",
        "error": "音訊錯誤：{message}", "saved_bad": "無法讀取的 W02 進度已備份，開始新草稿。",
        "save_error": "W02 無法儲存，原檔已保留。", "tier": "第 {n}/3 層幫助 · {text}",
    },
}


class MelodyWindow(QMainWindow):
    case_completed = Signal()
    device_requested = Signal(str)
    mode_changed = Signal(str)

    def __init__(self, *, case=None, save_path=None, player=None, renderer=None,
                 language="en", volume=.35, embedded=False):
        super().__init__()
        self.case = case or MelodyCase()
        self.save_path = Path(save_path or ROOT / "userdata/wordle"/(self.case.id+'.json'))
        self._language, self.embedded = language, embedded
        self._closed = self._save_blocked = False
        self._warning, self._revision, self._armed = "", None, None
        self.device_kind = "synth"
        try:
            self.session = load_melody_session(self.save_path,self.case)
        except (OSError, ValueError, TypeError, KeyError):
            self.session = MelodySession(case=self.case)
            try:
                SessionStore(self.save_path).preserve_invalid()
                self._warning = "saved_bad"
            except OSError:
                self._warning, self._save_blocked = "save_error", True
        self.player, self.renderer = player or AudioPlayer(self), renderer or PreviewRenderer(self)
        self._build(volume)
        from .edit_history import EditHistoryBar
        from ..game.edit_history import EditHistory
        self._edit_stacks = {mode: EditHistory(getattr(self.session, mode)) for mode in ('challenge', 'free')}
        self.edit_bar = EditHistoryBar(self, self.session.current, self._restore_edit,
                                       enabled=lambda: not self._closed)
        self.edit_bar.stack = self._edit_stacks[self.session.mode]
        self.renderer.ready.connect(self._ready)
        self.renderer.failed.connect(self._failed)
        self.player.state_changed.connect(self._player_state)
        self.player.state_changed.connect(self.deck.set_state)
        self.player.error.connect(lambda message: self.status.setText(self.t("error").format(message=message)))
        self.player.set_volume(volume)
        if not embedded:
            self.device_requested.connect(self.present_device)
        self._translate()
        self._save()

    def t(self, key):
        if self.case.id!='W02':
            zh=self._language=='zh-Hant'
            if key=='title':return 'Sound Detective · '+self.case.id+' · '+self.case.title[self._language]
            if key=='story':return self.case.story[self._language]
            if key=='solved':return self.case.completion[self._language]
            if key=='modes':return (self.case.id+(' 挑戰' if zh else ' challenge'),'自由創作' if zh else 'Free composition')
            if key=='rules':return ('只考節奏；音高與音色固定。不限提交，保留停頓。' if zh else 'Rhythm only; fixed pitch and timbre. Unlimited submissions; preserve the pause.') if self.case.stages==(0,) else ('節奏 → 音高；音色固定，不限提交。' if zh else 'Rhythm → pitch; fixed timbre and unlimited submissions.')
            if key=='hidden':return '本案達標後才開放目標。' if zh else 'Solve this case to reveal the target.'
            if key=='locked':return '本案音色已設定，請用鋼琴卷簾調整音符。' if zh else 'Timbre is already set. Use the piano roll to edit notes.'
            if key=='pitch_locked' and self.case.stages==(0,):return '本案固定 C4，只調整音符位置及長度。' if zh else 'This case keeps C4 fixed; edit note positions and lengths only.'
            if key=='ready' and self.session.focus==self.case.stages[-1]:return '目前已達要求，提交此版本即可完成案件。' if zh else 'The requirements are met. Submit this version to close the case.'
            if key in ('saved_bad','save_error'):return TEXT[self._language][key].replace('W02',self.case.id)
        return TEXT[self._language][key]

    def label(self):
        label = QLabel()
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        return label

    def _build(self, volume):
        body = QWidget()
        body.setObjectName("wordle_body")
        body.setStyleSheet("""
            QWidget#wordle_body QPushButton { padding: 6px 12px; }
            QWidget#wordle_body QComboBox { padding: 4px 6px; min-height: 18px; }
            QWidget#wordle_body QGroupBox { padding: 6px; }
            QWidget#wordle_body QTabBar::tab { padding: 5px 8px; }
        """)
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(5)
        top = QHBoxLayout()
        self.title = self.label()
        self.title.setStyleSheet("font-size: 18px; color: #efd6a0;")
        self.title.setVisible(not self.embedded)
        top.addWidget(self.title, 1)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("繁體中文", "zh-Hant")
        self.language.setCurrentIndex(self._language == "zh-Hant")
        self.language.currentIndexChanged.connect(self._change_language)
        self.language.setVisible(not self.embedded)
        top.addWidget(self.language)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(volume * 100))
        self.volume.setMaximumWidth(90)
        self.volume.valueChanged.connect(lambda value: self.player.set_volume(value / 100))
        self.volume.setVisible(not self.embedded)
        top.addWidget(self.volume)
        layout.addLayout(top)
        mode_row = QHBoxLayout()
        self.mode_buttons = {}
        for mode in ("challenge", "free"):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, key=mode: self._set_mode(key))
            self.mode_buttons[mode] = button
            mode_row.addWidget(button)
        self.tempo_label = QLabel()
        self.tempo = QSpinBox()
        self.tempo.setRange(60, 160)
        self.tempo.setFixedWidth(90)
        self.tempo_label.setMaximumWidth(40)
        self.tempo.valueChanged.connect(self._tempo_changed)
        mode_row.addWidget(self.tempo_label)
        mode_row.addWidget(self.tempo)
        layout.addLayout(mode_row)
        self.rules = self.label()
        self.rules.setStyleSheet("font-size: 12px; color: #bfb79f;")
        layout.addWidget(self.rules)
        self.navigation = QWidget()
        nav = QHBoxLayout(self.navigation)
        nav.setContentsMargins(0, 0, 0, 0)
        self.device_buttons = {}
        for key in ("synth", "filter", "delay", "reverb", "analyzer"):
            button = QPushButton()
            button.clicked.connect(lambda checked=False, device=key: self.present_device(device))
            self.device_buttons[key] = button
            nav.addWidget(button)
        self.navigation.setVisible(not self.embedded)
        layout.addWidget(self.navigation)
        columns = QHBoxLayout()
        self.notebook, self.machine = QGroupBox(), QGroupBox()
        self.notebook.setMaximumWidth(325)
        left, right = QVBoxLayout(self.notebook), QVBoxLayout(self.machine)
        left.setSpacing(4)
        self.story, self.score, self.cards, self.stale, self.stage_label = [self.label() for _ in range(5)]
        self.story.setStyleSheet("font-size: 13px;")
        self.score.setStyleSheet("font-size: 17px; color: #efd6a0;")
        self.stale.setStyleSheet("font-size: 12px; color: #bfb79f;")
        notes=QWidget();notes_layout=QVBoxLayout(notes);notes_layout.setContentsMargins(0,0,0,0)
        self.submission_feedback=SubmissionFeedback()
        for label in (self.story, self.stage_label, self.score, self.submission_feedback, self.cards, self.stale):
            notes_layout.addWidget(label)
        notes_layout.addStretch()
        self.note_scroll=QScrollArea();self.note_scroll.setWidgetResizable(True);self.note_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.note_scroll.setMinimumHeight(0);self.note_scroll.setWidget(notes);left.addWidget(self.note_scroll,1)
        self.play_reference, self.play_current, self.stop_button, self.play_ab = [QPushButton() for _ in range(4)]
        self.play_reference.clicked.connect(lambda: self._prepare("target"))
        self.play_current.clicked.connect(lambda: self._prepare("current"))
        self.play_ab.clicked.connect(lambda: self._prepare("ab"))
        self.stop_button.clicked.connect(self.stop)
        self.deck = PlaybackDeck(self.play_reference, self.play_current, self.stop_button, self.play_ab, compact=True)
        left.addWidget(self.deck)
        self.feedback = self.label()
        self.feedback.setStyleSheet("font-size: 13px;")
        self.feedback.setMaximumHeight(90)
        right.addWidget(self.feedback)
        hints = QHBoxLayout()
        self.hint_button, self.lesson_button, self.goto_button = [QPushButton() for _ in range(3)]
        self.hint_button.clicked.connect(self._hint)
        self.lesson_button.clicked.connect(lambda: self._prepare("lesson"))
        self.goto_button.clicked.connect(self._goto_suggested)
        for button in (self.hint_button, self.lesson_button, self.goto_button):
            hints.addWidget(button)
        right.addLayout(hints)
        self.work_tabs = QTabWidget()
        self.piano = PianoRollEditor()
        if self.case.id!='W02':self.piano.viewport.setMinimumHeight(125)
        self.piano.changed.connect(self._pattern_changed)
        self.piano.editing_started.connect(lambda: self.stop(cancel_drag=False))
        self.piano_scroll = QScrollArea()
        self.piano_scroll.setWidgetResizable(True)
        self.piano_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.piano_scroll.setWidget(self.piano)
        self.editor = ParameterEditor(self.case)
        self.editor.use_hardware_controls()
        self.controls = self.editor.controls
        self.editor.changed.connect(self._sound_changed)
        self.work_tabs.addTab(self.piano_scroll, "Piano roll")
        self.work_tabs.addTab(self.editor, "Synthesizer")
        right.addWidget(self.work_tabs, 1)
        self.locked = self.label()
        self.locked.setStyleSheet("font-size: 12px; color: #bfb79f;")
        right.addWidget(self.locked)
        self.history = QTableWidget(0, 4)
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.verticalHeader().hide()
        right.addWidget(self.history, 1)
        history_row = QHBoxLayout()
        self.restore_button, self.history_play = QPushButton(), QPushButton()
        self.restore_button.clicked.connect(self._restore)
        self.history_play.clicked.connect(lambda: self._prepare("history"))
        history_row.addWidget(self.restore_button)
        history_row.addWidget(self.history_play)
        right.addLayout(history_row)
        columns.addWidget(self.notebook, 3)
        columns.addWidget(self.machine, 8)
        layout.addLayout(columns, 1)
        bottom = QHBoxLayout()
        self.submit_button, self.history_button, self.reset_button = [QPushButton() for _ in range(3)]
        self.submit_button.clicked.connect(self._submit)
        self.history_button.clicked.connect(lambda: self.device_requested.emit("analyzer"))
        self.reset_button.clicked.connect(self._restart)
        for button in (self.submit_button, self.history_button, self.reset_button):
            bottom.addWidget(button)
        layout.addLayout(bottom)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedHeight(3)
        self.busy.hide()
        layout.addWidget(self.busy)
        self.status, self.save_warning = self.label(), self.label()
        self.status.setStyleSheet("font-size: 12px; color: #bfb79f;")
        layout.addWidget(self.status)
        layout.addWidget(self.save_warning)
        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.stop)
        self.shortcut.setEnabled(not self.embedded)
        self.resize(1220, 760)

    def _change_language(self, index):
        self._language = self.language.itemData(index)
        self._translate()

    def _translate(self):
        from .hover_help import apply_window_help
        self.setWindowTitle(self.t("title"))
        self.title.setText(self.t("title"))
        self.notebook.setTitle(self.t("notebook"))
        self.machine.setTitle(self.case.title[self._language])
        self.story.setText(self.t("story"))
        self.tempo_label.setText(self.t("tempo"))
        for key, text in zip(self.mode_buttons, self.t("modes")):
            self.mode_buttons[key].setText(text)
        self.mode_buttons['free'].setVisible(self.case.id=='W02')
        for button, text in zip(self.device_buttons.values(), self.t("devices")):
            button.setText(text)
        for button, key in ((self.play_current, "current"), (self.play_ab, "ab"), (self.stop_button, "stop"),
                            (self.hint_button, "hint"), (self.lesson_button, "lesson"), (self.goto_button, "next"),
                            (self.submit_button, "submit"), (self.history_button, "history"), (self.reset_button, "reset"),
                            (self.restore_button, "restore"), (self.history_play, "hear")):
            button.setText(self.t(key))
        for i, text in enumerate(self.t("tabs")):
            self.work_tabs.setTabText(i, text)
        self.editor.translate(self._language)
        self.piano.translate(self._language)
        self.deck.translate(self._language)
        self.status.setText(self.t("initial"))
        self._refresh(history=True)
        apply_window_help(self, "melody", self._language)
        if self.case.id!='W02':
            self.mode_buttons['challenge'].setToolTip('返回本案的獨立挑戰草稿，不會改動 W02 自由創作。' if self._language=='zh-Hant' else 'Resume this case draft without changing W02 free composition.')

    def _refresh(self, *, history=False):
        s, free = self.session, self.session.mode == "free"
        def snapshot(record):
            if record is None:return None
            result=compare_draft(Draft.from_dict(record['draft']),self.case)
            labels=('rhythm','melody','timbre')
            return ScoreSnapshot(result.total,{labels[i]:result.scores[i] for i in self.case.stages},self.case.fingerprint or 'W02-v1',record['number'])
        names=dict(zip(('rhythm','melody','timbre'),self.t('groups')))
        self.submission_feedback.show_scores(snapshot(s.records[-1]) if s.records and not free else None,
            snapshot(s.records[-2]) if len(s.records)>1 and not free else None,language=self._language,labels=names)
        self.notebook.setTitle(self.t("free_notebook" if free else "notebook"))
        self.machine.setTitle(self.t("free_machine") if free else self.case.title[self._language])
        self.rules.setText(self.t("free_rules" if free else "rules"))
        self.stage_label.setText(self.t("free") if free else self.t("stages")[s.focus])
        self.stage_label.setVisible(not free)
        self.story.setVisible(not free)
        for key, button in self.mode_buttons.items():
            button.setChecked(s.mode == key)
        self.tempo.blockSignals(True)
        self.tempo.setValue(s.current.tempo)
        self.tempo.blockSignals(False)
        self.tempo.setEnabled(free)
        self.editor.set_settings(s.current.sound)
        self.editor.set_locked(not free and s.unlocked < 2)
        rhythm_hints = tuple((n.start, n.length) for n in self.case.pattern.notes) if not free and s.hints[0] >= (2 if self.case.id=='W02' else 3) else ()
        hint_notes = (self.case.pattern.notes[0], self.case.pattern.notes[-1]) if not free and s.hints[1] >= 2 else ()
        if self.case.id!='W02' and s.hints[1]==2:hint_notes=(self.case.pattern.notes[0],)
        self.piano.set_pattern(s.current.pattern, pitch_locked=not free and s.unlocked == 0,
                               rhythm_hints=rhythm_hints, hint_notes=hint_notes)
        if 1 not in self.case.stages:
            self.piano.instructions.setText('拖移改起點，拉兩側改長度；音高固定。' if self._language=='zh-Hant' else 'Drag to move; pull either edge for length. Pitch stays fixed.')
        self.score.setText(self.t("free") if free else self.t("unscored"))
        self.cards.clear()
        if s.records and not free:
            result = compare_draft(Draft.from_dict(s.records[-1]["draft"]),self.case)
            self.score.setText(self.t("score").format(n=s.attempts, score=f"{math.floor(result.total * 10) / 10:.1f}"))
            self.cards.setText("\n".join(f"{self.t('groups')[i]}: {result.scores[i]:.1f} / 100" for i in self.case.stages))
        self.stale.setText(self.t("stale"))
        self.stale.setVisible(not free and bool(s.records) and not s.current_is_submitted)
        self.play_reference.setText(self.t("target_open" if s.solved else "target"))
        self.play_reference.setEnabled(s.solved and not free)
        self.play_ab.setEnabled(s.solved and not free)
        self.submit_button.setEnabled(not free)
        self.hint_button.setEnabled(not free)
        self.goto_button.setVisible(not free)
        self.history_button.setEnabled(bool(s.records))
        self.save_warning.setVisible(bool(self._warning))
        self.save_warning.setText(self.t(self._warning) if self._warning else "")
        self._show_clue()
        if history:
            self.history.setHorizontalHeaderLabels(self.t("columns"))
            self.history.setRowCount(len(s.records))
            for row, record in enumerate(s.records):
                result = compare_draft(Draft.from_dict(record["draft"]),self.case)
                for column, value in enumerate((str(record["number"]), *(f"{v:.1f}" if i in self.case.stages else '—' for i,v in enumerate(result.scores)))):
                    self.history.setItem(row, column, QTableWidgetItem(value))
            if s.records:
                self.history.setCurrentCell(len(s.records) - 1, 0)
        self.restore_button.setEnabled(bool(s.records))
        self.history_play.setEnabled(bool(s.records))
        self.present_device(self.device_kind)

    def present_device(self, device):
        self.device_kind = device
        analyzing = device == "analyzer"
        workshop = device in ("synth", "tape")
        self.work_tabs.setVisible(not analyzing)
        self.history.setVisible(analyzing)
        self.restore_button.setVisible(analyzing)
        self.history_play.setVisible(analyzing)
        self.work_tabs.setTabVisible(0, workshop)
        self.work_tabs.setTabVisible(1,self.session.mode=='free' or 2 in self.case.stages)
        self.editor.show_groups({"harmonics", "envelope", "filter"} if workshop else {device})
        self.locked.setText(self.t("pitch_locked") if self.session.unlocked == 0 and workshop else self.t("locked"))
        self.locked.setVisible(not analyzing and self.session.mode == "challenge" and self.session.unlocked < 2)

    def _show_clue(self):
        s, zh = self.session, self._language == "zh-Hant"
        if s.mode == "free":
            self.feedback.setText(self.t("free_help"))
            guidance(self).show_targets()
            return
        result, stage = compare_draft(s.challenge,self.case), s.focus
        tier = s.hints[stage]
        self.feedback.setStyleSheet('')
        if all(result.passed) and s.current_is_submitted:
            text = self.t("solved")
            self.feedback.setStyleSheet('color: #afd8b2; font-size: 16px;')
        elif result.passed[stage]:
            text = self.t("ready")
        elif self.case.clues is not None:
            text=authored_melody_clue(self.case,s.challenge,result,stage,tier,self._language)
        elif stage == 0:
            text = "四個音各在一拍的開頭；最後一音較長。" if zh else "Four onsets, one per beat; the last note is longer."
            if tier >= 1:
                delta = len(s.challenge.pattern.notes) - len(self.case.pattern.notes)
                text += (" 目前音符太多。" if delta > 0 else " 目前音符不足。" if delta < 0 else " 請檢查位置與長度。") if zh else (
                    " Too many notes." if delta > 0 else " More notes are needed." if delta < 0 else " Check positions and lengths.")
            if tier >= 2:
                text += " 金色底線標記節奏；每拍 4 格。" if zh else " Gold baseline marks show the rhythm; each beat has 4 cells."
            if tier >= 3:
                text += " 前三音各 2 格，最後一音 4 格。" if zh else " First three notes: 2 cells each. Last note: 4 cells."
        elif stage == 1:
            text = "旋律先上行兩次，再下行。" if zh else "The melody rises twice, then falls."
            if tier >= 1:
                wrong = next(((i, j) for i, j, _ in result.pairs if self.case.pattern.notes[i].pitch != s.challenge.pattern.notes[j].pitch), None)
                if wrong:
                    i, j = wrong
                    higher = s.challenge.pattern.notes[j].pitch < self.case.pattern.notes[i].pitch
                    text += (f" 第 {j+1} 音可再{'提高' if higher else '降低'}。" if zh else f" Move note {j+1} {'up' if higher else 'down'}.")
                text += " 音域 C4–G4。" if zh else " Range: C4–G4."
            if tier >= 2:
                text += " 虛線給出第一與最後一音。" if zh else " Dashed notes reveal the first and last pitches."
            if tier >= 3:
                text += " 第二音比第一音高 4 半音；第三音再高 3 半音。" if zh else " Note 2 is 4 semitones above note 1; note 3 rises another 3 semitones."
        else:
            if result.timbre is None:
                text = self.t("empty")
            else:
                code = result.timbre.diagnostics[0]
                text = PROGRESS_CLUES[code][zh]
                if tier >= 2:
                    text += " 音色要求：短促、明亮、輕微回聲；Filter 與 Reverb 關閉。" if zh else " Aim for short, bright, gentle echo; Filter and Reverb off."
                if tier >= 3:
                    text += " 先完成開關，再小幅調旋鈕；一次改一項。" if zh else " Correct switches first, then adjust one knob at a time."
        if tier:
            text = self.t("tier").format(n=tier, text=text)
        if s.solved and not all(result.passed):
            text = self.t("practice") + " " + text
        self.feedback.setText(text)
        self.feedback.setToolTip(text)
        keys=();extra=();device=''
        if tier and not result.passed[stage]:
            if stage<2:
                extra=(self.piano.viewport,self.piano.pitch) if stage==1 else (self.piano.viewport,self.piano.start,self.piano.length)
                if not s.challenge.pattern.notes:extra=(self.piano.add_button,)
                device='synth'
            elif result.timbre:
                key=progress_control(result.timbre.diagnostics[0])
                if key:keys=(key,);device=device_for(key)
        guidance(self).show_targets(self.editor,keys,device,extra)

    def _update(self, draft):
        self.stop()
        try:
            self.session.update(draft)
            self.edit_bar.record(self.session.current)
        except ValueError:
            self.status.setText(self.t("locked"))
        self._refresh()
        self._save()

    def _pattern_changed(self, pattern):
        current = self.session.current
        self._update(Draft(pattern, current.sound, current.tempo))

    def _restore_edit(self, draft):
        self.stop()
        self.session.update(draft)
        self._refresh()
        self._save()

    def _sound_changed(self):
        current = self.session.current
        self._update(Draft(current.pattern, self.case.settings(**self.editor.values()), current.tempo))

    def _tempo_changed(self, value):
        current = self.session.current
        self._update(Draft(current.pattern, current.sound, value))

    def _set_mode(self, mode):
        if mode=='free' and self.case.id!='W02':return
        changed = self.session.mode != mode
        self.stop()
        self.session.set_mode(mode)
        self.edit_bar.stack = self._edit_stacks[mode]
        self.edit_bar.stack.break_merge()
        self.edit_bar.refresh()
        self._refresh()
        self._save()
        if changed:
            self.mode_changed.emit(mode)

    def _submit(self):
        was_solved = self.session.solved
        self.stop()
        try:
            result = self.session.submit()
        except ValueError:
            self.status.setText(self.t("empty"))
            return
        if result is None:
            return
        self._refresh(history=True)
        QTimer.singleShot(0,lambda:self.note_scroll.ensureWidgetVisible(self.score) if not self._closed else None)
        self.status.setText(self.t("solved" if all(result.passed) else "submitted"))
        self._save()
        if not was_solved and self.session.solved:
            self.case_completed.emit()

    def _hint(self):
        self.session.request_hint()
        self._refresh()
        if self.session.mode!='free' and self.session.focus<2 and self.session.current.pattern.notes:
            result=compare_draft(self.session.current,self.case)
            index=next((j for i,j,_ in result.pairs if self.session.focus==1 and
                self.case.pattern.notes[i].pitch!=self.session.current.pattern.notes[j].pitch),0)
            # Select an existing player note, never insert a reference note or
            # change its pitch/timing. Its inspector and drag handles light up.
            self.piano.roll.selection=index;self.piano.roll.selected.emit()
            self.piano._reveal_selection();self._show_clue()
        self._save()

    def _goto_suggested(self):
        stage = self.session.focus
        device = "synth"
        if stage == 2:
            result = compare_draft(self.session.challenge,self.case)
            if result.timbre:
                group = min(result.timbre.modules, key=result.timbre.modules.get)
                device = group if group in ("delay", "reverb") else "synth"
                if device == "synth":
                    self.editor.tabs.setCurrentIndex(self.editor._tab_groups.index(group))
        self.device_requested.emit(device)
        if device == "synth":
            self.work_tabs.setCurrentIndex(0 if stage < 2 else 1)

    def _restore(self):
        row = self.history.currentRow()
        if row >= 0:
            previous_mode = self.session.mode
            self.stop()
            self.session.restore(row)
            self.edit_bar.stack = self._edit_stacks[self.session.mode]
            self.edit_bar.record(self.session.current, merge=False)
            self._refresh()
            self._save()
            if previous_mode != self.session.mode:
                self.mode_changed.emit(self.session.mode)

    def _restart(self):
        self.stop()
        self.session.reset()
        self.edit_bar.reset(self.session.current)
        self._refresh(history=True)
        self._save()

    def _prepare(self, mode):
        if self._closed:
            return
        if mode in ("target", "ab") and (not self.session.solved or self.session.mode == "free"):
            self.status.setText(self.t("hidden"))
            return
        self.stop()
        if mode == "lesson":
            requests = dict(zip(("lesson1", "lesson2"), teaching_pair(self.session.focus)))
        elif mode == "history":
            row = self.history.currentRow()
            if row < 0:
                return
            draft = Draft.from_dict(self.session.records[row]["draft"])
            requests = {"history": (draft.sound, draft.sequence)}
        else:
            draft = self.session.current
            if mode != "target" and (not draft.pattern.notes or draft.sound.patch.is_silent):
                self.status.setText(self.t("empty"))
                return
            requests = {}
            if mode in ("target", "ab"):
                requests["target"] = (self.case.reference, self.case.sequence)
            if mode in ("current", "ab"):
                requests["current"] = (draft.sound, draft.sequence)
        self._armed = tuple(requests)
        self.busy.show()
        try:
            self._revision = self.renderer.prepare(requests)
            self.status.setText(self.t("lesson_note" if mode == "lesson" else "generating"))
        except (OSError, ValueError, RuntimeError) as error:
            self._failed(self._revision, str(error))

    def _ready(self, revision, previews):
        if self._closed or revision != self._revision or self._armed is None:
            return
        labels, self._armed = self._armed, None
        self.busy.hide()
        try:
            self.player.play([PlaybackItem(previews[key].listening_path, key) for key in labels])
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            self.status.setText(self.t("error").format(message=str(error)))

    def _failed(self, revision, message):
        if not self._closed and revision == self._revision:
            self._armed = None
            self.busy.hide()
            self.status.setText(self.t("error").format(message=message))

    def _player_state(self, state, label):
        if not self._closed and state in ("playing", "loading"):
            if label.startswith("lesson"):
                self.status.setText(self.t("lesson_note") + f" ({label[-1]}/2)")
            else:
                self.status.setText(self.t("playing").format(label=self.t("current" if label == "current" else "target_open") if label != "history" else self.t("hear")))

    def stop(self, *, cancel_drag=True):
        if cancel_drag:
            self.piano.roll.cancel_drag()
        self._revision = self._armed = None
        self.renderer.cancel()
        self.player.stop()
        self.busy.hide()
        self.status.setText(self.t("stopped"))

    def _save(self):
        if not self._save_blocked:
            try:
                save_melody_session(self.save_path, self.session)
            except (OSError, ValueError):
                self._warning = "save_error"
                self.save_warning.setText(self.t("save_error"))
                self.save_warning.show()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowDeactivate and hasattr(self, "player") and not self.embedded:
            QTimer.singleShot(0, lambda: self.stop() if not self._closed and not self.isActiveWindow() else None)

    def closeEvent(self, event):
        if not self._closed:
            self.stop()
            self._save()
            self._closed = True
            self.player.close()
            self.renderer.close()
        event.accept()
