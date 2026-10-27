"""Guided music restoration: effects, pitch, then full-song playback."""

import json
import shutil
import uuid
from types import SimpleNamespace

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QCheckBox, QDoubleSpinBox,
    QHBoxLayout, QLabel, QMainWindow, QProgressBar, QPushButton,
    QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget)

from ..audio.models import SoundSettings
from ..audio.music_preview import MusicPreviewRenderer
from ..audio.playback import AudioPlayer, PlaybackItem
from ..audio.sc_client import ROOT
from ..game.music_cases import (MusicSession, MusicSettings, load_music_case,
                                PITCH_STAGE_TOLERANCE_CENTS)
from ..game.music_repair import GROUP_NAMES, RepairSettings
from ..game.recorded_pitch import load_recorded_pitch_map
from ..game.parameters import PARAMETERS, replace_parameters
from ..game.storage import SessionStore, atomic_json_write
from .music_repair_editor import MusicRepairEditor
from .recorded_pitch_roll import RecordedPitchEditor


TEXT = {
    "en": {
        "title": "Sound Detective — Music case {id}", "clues": "Your current task",
        "rules": "Restore filter, echo and reverb first, then tune the notes. Finish every stage to unlock the full original song.",
        "evidence": "Distorted evidence", "current": "My repair",
        "pitch": "Pitch calibration", "effects": "Repair devices", "repair_log": "Calibration log",
        "check_repair": "Check & get a clue", "repair_pending": "Check your current step for progress and a tuning direction. Future devices unlock after submission.",
        "repair_stale": "Controls changed. Check calibration again to update the repair log.",
        "repair_total": "Current step: {score:.1f} / 100", "migration": "Old progress was backed up. Passed effects, pitch drafts and previous records were retained; continue in the new effects-first order.",
        "pitch_note": "Drag note blocks up/down · Shift: fine tuning · double-click: hear note. Grey notes are context.",
        "submit": "Submit current step", "reset": "Restart restoration",
        "replay": "Play full song again", "volume": "Output volume", "idle": "Work on the current step. Check for a clue whenever you need one.",
        "generating": "Generating preview… You can keep editing; older previews will be cancelled.",
        "updated": "Controls changed. Listen to the reconstruction to hear the update.",
        "solved": "Restoration complete — {song} · submissions: {n}",
        "restored": "Restoration previously completed — {song}. Use Play full song again to listen.",
        "full": "Full song playing on repeat. Escape or closing this window ends playback.",
        "playing": "Playing · {label}", "stopped": "Playback stopped.", "error": "Error: {message}",
        "save_error": "Progress could not be saved: {message}",
        "backup": "Unreadable progress was preserved as a backup. A new investigation has started.",
        "device": "Output: {name}", "none": "No output device", "attempt_count": "Submissions: {n} · unlimited attempts",
        "stage": "Step {index}/{count} · {name}", "complete": "All restoration steps complete",
        "goto": "Open current device", "ready_submit": "Calibrated. Submit this step to continue.",
        "passed": "{name} cleared · {score:.1f}/100. Next: {next}.",
        "failed": "Submission {n} · {name}: {score:.1f}/100. Follow the clue and try again.",
        "pitch_count": "Regions within tolerance: {done}/{total} · threshold: 90/100 and every region within ±25 cents",
        "effect_goal": "Calibrate this device to at least 90/100, then submit. Completed repairs stay in place.",
        "locked": "This device is locked for now. Use Open current device to continue your current step.",
        "done": "Cleared", "future": "Locked", "pitch_task": "Finally tune the marked notes. Completed effect repairs stay in place.",
        "pitch_help": "Select a green note and drag vertically to change pitch. Shift-drag for fine tuning; double-click to hear it.",
        "fx_task": "Work only on {name}. Pitch calibration unlocks after the effects; later devices remain locked.",
        "fx_help": "Enable this repair device, adjust its estimates and check your progress. Switching it off keeps its damage.",
        "region_playing": "Pitch region monitor · effects isolated",
    },
    "zh-Hant": {
        "title": "Sound Detective — 音樂案件 {id}", "clues": "目前任務",
        "rules": "先修復濾波、回聲與混響，最後校正音高；完成所有步驟後，播放完整原曲。",
        "evidence": "扭曲證物", "current": "目前還原",
        "pitch": "音高校準", "effects": "修復設備", "repair_log": "校準記錄",
        "check_repair": "檢查並取得提示", "repair_pending": "檢查目前步驟的進度與調整方向；提交達標後才開放下一台設備。",
        "repair_stale": "設定已修改，請再次檢查校準，更新修復記錄。",
        "repair_total": "目前步驟：{score:.1f} / 100", "migration": "舊進度已備份，保留已通過的效果步驟、校音草稿與先前記錄；依先效果、後音高的新順序繼續。",
        "pitch_note": "上下拖曳音塊調音；Shift 細調；雙擊試聽。灰色音塊是上下文參照。",
        "submit": "提交目前步驟", "reset": "重新修復",
        "replay": "再次播放完整歌曲", "volume": "輸出音量", "idle": "依目前步驟操作；需要時可隨時檢查提示。",
        "generating": "正在生成試聽… 可繼續調整，過期試聽會自動取消。",
        "updated": "設定已修改；點擊聆聽目前還原，試聽新設定。",
        "solved": "音樂還原完成 — {song} · 已提交 {n} 次",
        "restored": "此音樂已還原完成 — {song}。可再次播放完整歌曲。",
        "full": "正在循環播放完整歌曲。按 Escape 或關閉此視窗可結束播放。",
        "playing": "播放中 · {label}", "stopped": "已停止播放。", "error": "錯誤：{message}",
        "save_error": "進度無法儲存：{message}",
        "backup": "無法讀取的進度已保留為備份，目前已開始新調查。",
        "device": "輸出裝置：{name}", "none": "沒有輸出裝置", "attempt_count": "已提交 {n} 次 · 不限次數",
        "stage": "步驟 {index}/{count} · {name}", "complete": "所有修復步驟已完成",
        "goto": "前往目前設備", "ready_submit": "校準已達標，提交這一步即可繼續。",
        "passed": "{name}已完成 · {score:.1f}/100。下一步：{next}。",
        "failed": "第 {n} 次提交 · {name}：{score:.1f}/100。依提示調整後再試。",
        "pitch_count": "容差內片段：{done}/{total} · 須達 90 分，且每段誤差均在 ±25 cents 內",
        "effect_goal": "將這台設備校準至至少 90 分，再提交。已完成的修復會保持。",
        "locked": "這台設備目前尚未開放，請按「前往目前設備」繼續當前步驟。",
        "done": "已完成", "future": "未開放", "pitch_task": "最後校正標記的音符；已完成的效果修復會保持。",
        "pitch_help": "選中綠色音塊，上下拖曳改變音高；Shift 拖曳可細調，雙擊即可試聽。",
        "fx_task": "現在只處理{name}；效果修復完成後才開放音高校正，後面的設備暫時鎖定。",
        "fx_help": "啟用這台修復器，調整估計值並檢查進度；關閉修復器會保留損傷。",
        "region_playing": "音高片段監聽 · 已隔離效果",
    },
}


class MusicCaseWindow(QMainWindow):
    case_completed = Signal()
    device_requested = Signal(str)

    def __init__(self, parent=None, *, case=None, player=None, renderer=None, save_path=None,
                 language=None, volume=None):
        super().__init__(parent)
        self._submission_snapshots={}
        self._submitted_feedback=None
        self.case = case or load_music_case()
        self.pitch_map = load_recorded_pitch_map(self.case)
        self.session = MusicSession(self.case)
        self.save_path = save_path or ROOT / "userdata/music" / f"{self.case.id}.json"
        self.store = SessionStore(self.save_path)
        self._language, self._volume = "en", .35
        self._closed = self._initializing = False
        self._revision = None
        self._backup = self._save_problem = None
        self._migration_backup = None
        self._repair_report = None
        self._repair_stale = False
        self._save_blocked = False
        self._result_kind = None
        self._pitch_index = 0
        self._status_key, self._status_args = "idle", {}
        self._load()
        self._audition_jobs, self._audition_items = [], []
        self._reset_comparison()
        if language is not None:
            self._language = language
        if volume is not None:
            self._volume = volume
        if self._language not in TEXT or not 0 <= self._volume <= 1:
            raise ValueError("Invalid music window preferences")
        self.player = player if player is not None else AudioPlayer(self)
        self.renderer = renderer if renderer is not None else MusicPreviewRenderer(self)
        self._initializing = True
        self.resize(1280, 720)
        self.setMinimumSize(1060, 650)
        self._build()
        from .edit_history import EditHistoryBar
        self.edit_bar = EditHistoryBar(self, self.session.settings, self._restore_edit,
            enabled=lambda: not self._closed and not self.session.solved, layout=self.footer)
        self._initializing = False
        self.renderer.ready.connect(self._ready)
        self.renderer.failed.connect(self._failed)
        self.player.state_changed.connect(self._player_state)
        self.player.error.connect(lambda message: self._status("error", message=message))
        self.player.device_changed.connect(lambda _: self._translate_device())
        self.player.set_volume(self._volume)
        self._translate()

    def _load(self):
        path = self.store.path
        if not path.exists():
            return
        try:
            if path.stat().st_size > 1_000_000:
                raise ValueError("Music progress too large")
            data = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(data, dict) or set(data) != {"schema_version", "session", "language", "volume"}
                    or type(data["schema_version"]) is not int or data["schema_version"] != 1
                    or data["language"] not in TEXT or isinstance(data["volume"], bool)
                    or not isinstance(data["volume"], (float, int)) or not 0 <= data["volume"] <= 1):
                raise ValueError("Invalid music preferences")
            self.session = MusicSession.from_dict(data["session"], self.case)
            if self.session.migrated:
                label = "effects-first" if data["session"]["schema_version"] == 3 else "staged-music"
                self._migration_backup = path.with_name(f"{path.stem}.before-{label}-{uuid.uuid4().hex[:8]}.json")
                try:
                    shutil.copy2(path, self._migration_backup)
                except OSError as error:
                    self._migration_backup = None
                    self._save_blocked, self._save_problem = True, str(error)
            self._language, self._volume = data["language"], data["volume"]
            if self.session.solved:
                self._result_kind = "restored"
        except (OSError, ValueError, TypeError, KeyError):
            try:
                self._backup = self.store.preserve_invalid()
            except OSError as error:
                self._save_blocked, self._save_problem = True, str(error)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        self.title = QLabel()
        font = self.title.font()
        font.setPointSize(17)
        font.setBold(True)
        self.title.setFont(font)
        heading.addWidget(self.title, 1)
        self.language = QComboBox()
        self.language.setObjectName("music_language")
        self.language.addItem("English", "en")
        self.language.addItem("繁體中文", "zh-Hant")
        self.language.setCurrentIndex(0 if self._language == "en" else 1)
        self.language.currentIndexChanged.connect(self._change_language)
        heading.addWidget(self.language)
        layout.addLayout(heading)
        self.rules = QLabel()
        self.rules.setWordWrap(True)
        layout.addWidget(self.rules)
        self.stage_banner = QLabel()
        self.stage_banner.setWordWrap(True)
        layout.addWidget(self.stage_banner)
        body = QHBoxLayout()
        self.clue_group = QGroupBox()
        left = QVBoxLayout(self.clue_group)
        clue_body = QWidget()
        clue_layout = QVBoxLayout(clue_body)
        clue_layout.setContentsMargins(0, 0, 2, 0)
        from .investigation_feedback import SubmissionFeedback
        self.submission_feedback=SubmissionFeedback()
        clue_layout.addWidget(self.submission_feedback)
        self.clue_labels = []
        for _ in range(3):
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            clue_layout.addWidget(label)
            self.clue_labels.append(label)
        clue_layout.addStretch()
        self.clue_scroll = QScrollArea()
        self.clue_scroll.setWidgetResizable(True)
        self.clue_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.clue_scroll.setMinimumHeight(70)
        self.clue_scroll.setWidget(clue_body)
        left.addWidget(self.clue_scroll, 1)
        self.play_evidence = QPushButton()
        self.play_evidence.setObjectName("play_music_evidence")
        self.play_evidence.clicked.connect(self._play_evidence)
        self.play_current = QPushButton()
        self.play_current.setObjectName("play_music_reconstruction")
        self.play_current.clicked.connect(self._play_current)
        left.addWidget(self.play_evidence)
        left.addWidget(self.play_current)
        self.check_repair_button = QPushButton()
        self.check_repair_button.setObjectName("check_music_repair")
        self.check_repair_button.clicked.connect(self._help_and_focus)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.hide()
        left.addWidget(self.busy)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        left.addWidget(self.status)
        body.addWidget(self.clue_group, 2)
        self.tabs = QTabWidget()
        pitch_page = QWidget()
        pitch_layout = QVBoxLayout(pitch_page)
        pitch_layout.setSpacing(5)
        self.pitch_note = QLabel()
        self.pitch_note.setWordWrap(True)
        pitch_layout.addWidget(self.pitch_note)
        self.pitch_editor = RecordedPitchEditor(self.pitch_map, tuple(r.cents for r in self.case.regions), self.session.settings.corrections)
        self.pitch_editor.changed.connect(self._controls_changed)
        self.pitch_editor.selection_changed.connect(self._select_region)
        self.pitch_editor.editing_started.connect(self._invalidate)
        self.pitch_editor.audition_requested.connect(self._play_region)
        self.play_region_button = self.pitch_editor.audition_button
        pitch_layout.addWidget(self.pitch_editor, 1)
        self.pitch_count = QLabel(pitch_page)
        self.pitch_count.hide()
        self.stage_hint = QLabel()
        self.stage_hint.setWordWrap(True)
        self.stage_hint.setTextFormat(Qt.TextFormat.PlainText)
        pitch_layout.addWidget(self.stage_hint)
        self.tabs.addTab(pitch_page, "")
        keys = tuple(key for key, spec in PARAMETERS.items() if spec.group in {"filter", "delay", "reverb"})
        adapter = SimpleNamespace(initial=SoundSettings(effects=self.session.settings.repair.estimates), editable_parameters=keys)
        self.effects_editor = MusicRepairEditor(adapter)
        self.effects_editor.changed.connect(self._controls_changed)
        self.tabs.addTab(self.effects_editor, "")
        self.repair_result = QLabel()
        self.repair_result.setWordWrap(True)
        self.repair_result.setTextFormat(Qt.TextFormat.PlainText)
        self.repair_result.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.repair_result.setMargin(14)
        repair_page = QScrollArea()
        repair_page.setWidgetResizable(True)
        repair_page.setWidget(self.repair_result)
        self.tabs.addTab(repair_page, "")
        body.addWidget(self.tabs, 5)
        layout.addLayout(body, 1)
        monitor_page = QWidget()
        monitor_layout = QVBoxLayout(monitor_page)
        monitor_layout.setContentsMargins(18, 18, 18, 18)
        monitor = QHBoxLayout()
        self.range_label = QLabel()
        self.range_start, self.range_end = QDoubleSpinBox(), QDoubleSpinBox()
        for control, value in ((self.range_start, 0), (self.range_end, self.case.seconds)):
            control.setRange(0, self.case.seconds)
            control.setDecimals(2)
            control.setSingleStep(.1)
            control.setSuffix(' s')
            control.setValue(value)
            control.setFixedWidth(90)
            control.valueChanged.connect(self._range_changed)
        self.loop_preview = QCheckBox()
        self.loop_preview.toggled.connect(lambda _: self._invalidate())
        self.note_range_button, self.ab_version_button = QPushButton(), QPushButton()
        self.pin_version_button, self.restore_version_button = QPushButton(), QPushButton()
        self.note_range_button.clicked.connect(self._use_note_range)
        self.ab_version_button.clicked.connect(self._play_versions)
        self.pin_version_button.clicked.connect(self._pin_version)
        self.restore_version_button.clicked.connect(lambda: self._restore_edit(self._reference_settings))
        for widget in (self.range_label, self.range_start, self.range_end, self.loop_preview, self.note_range_button):
            monitor.addWidget(widget)
        monitor.addStretch()
        monitor_layout.addLayout(monitor)
        versions = QHBoxLayout()
        for widget in (self.ab_version_button, self.pin_version_button, self.restore_version_button):
            versions.addWidget(widget)
        monitor_layout.addLayout(versions)
        self.comparison_feedback = QLabel()
        self.comparison_feedback.setWordWrap(True)
        monitor_layout.addWidget(self.comparison_feedback)
        monitor_layout.addStretch()
        self.tabs.addTab(monitor_page, '')
        actions = QHBoxLayout()
        self.action_row=actions
        self.goto_button = QPushButton()
        self.goto_button.clicked.connect(self._goto_stage)
        self.submit_button = QPushButton()
        self.submit_button.setObjectName("submit_music_stage")
        self.submit_button.clicked.connect(self._submit)
        actions.addWidget(self.goto_button)
        actions.addWidget(self.check_repair_button)
        actions.addWidget(self.submit_button, 1)
        layout.addLayout(actions)
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.result)
        footer = QHBoxLayout()
        self.footer = footer
        self.volume_label = QLabel()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(self._volume * 100))
        self.volume.valueChanged.connect(self._volume_changed)
        self.device = QLabel()
        self.reveal_button = QPushButton()
        self.reveal_button.setObjectName("replay_full_song")
        self.reveal_button.clicked.connect(self._play_reveal)
        self.restart_button = QPushButton()
        self.restart_button.clicked.connect(self._restart)
        for widget in (self.volume_label, self.volume, self.device, self.reveal_button, self.restart_button):
            footer.addWidget(widget)
        layout.addLayout(footer)
        self.save_warning = QLabel()
        self.save_warning.setWordWrap(True)
        self.save_warning.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.save_warning)
        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.stop)

    def _translate(self):
        from .hover_help import apply_window_help
        text = TEXT[self._language]
        self.setWindowTitle(text["title"].format(id=self.case.id))
        self.title.setText(f"{self.case.id} · {self.case.title[self._language]}")
        self.rules.setText(text["rules"])
        self.clue_group.setTitle(text["clues"])
        for widget, key in ((self.play_evidence, "evidence"), (self.play_current, "current"),
                            (self.submit_button, "submit"), (self.reveal_button, "replay"),
                            (self.restart_button, "reset"), (self.volume_label, "volume"), (self.pitch_note, "pitch_note")):
            widget.setText(text[key])
        for widget, key in ((self.goto_button, "goto"),):
            widget.setText(text[key])
        self.check_repair_button.setText(text["check_repair"])
        self.tabs.setTabText(0, text["pitch"])
        self.tabs.setTabText(1, text["effects"])
        self.tabs.setTabText(2, text["repair_log"])
        self._show_repair()
        self.pitch_editor.translate(self._language)
        self.effects_editor.translate(self._language)
        self._translate_device()
        self._show_result()
        self._show_stage()
        self._status(self._status_key, **self._status_args)
        self._show_save_warning()
        self._lock()
        apply_window_help(self, "music", self._language)
        self._translate_monitor()

    def _translate_monitor(self):
        from .hover_help import set_help
        zh = self._language == 'zh-Hant'
        self.tabs.setTabText(3, '試聽對比' if zh else 'Audition & versions')
        self.tabs.setTabToolTip(3, '循環試聽片段，並比較自己的前後版本。' if zh else 'Loop a passage and compare your before and after versions.')
        for widget, en, tc, key in (
            (self.range_label, 'Range', '範圍', 'music_range'),
            (self.loop_preview, 'Loop repair', '循環還原', 'music_loop'),
            (self.note_range_button, 'Selected note', '選中音符', 'music_note_range'),
            (self.ab_version_button, 'Before → now', '之前 → 目前', 'music_ab'),
            (self.pin_version_button, 'Remember version', '記住版本', 'music_pin'),
            (self.restore_version_button, 'Restore version', '恢復版本', 'music_restore')):
            widget.setText(tc if zh else en)
            set_help(widget, key, self._language)
        for control in (self.range_start, self.range_end):
            set_help(control, 'music_range', self._language)
        self._show_comparison()

    def _translate_device(self):
        text = TEXT[self._language]
        self.device.setText(text["device"].format(name=self.player.device_name or text["none"]))

    def _status(self, key, **arguments):
        self._status_key, self._status_args = key, arguments
        if key == "repair_hint":
            module = next((item for item in self._repair_report.modules if item.group == self.session.stage), None) if self._repair_report else None
            self.status.setText(module.hint(self._language) if module else TEXT[self._language]["repair_pending"])
            return
        self.status.setText(TEXT[self._language][key].format(**arguments))

    def _show_result(self):
        text = TEXT[self._language]
        if self.session.solved:
            self._result_kind = self._result_kind or "restored"
            self.result.setText(text[self._result_kind].format(song=self.case.answers[0], n=self.session.attempts))
        elif self.session.last:
            last = self.session.last
            name = GROUP_NAMES[last.stage][self._language == "zh-Hant"]
            next_name = GROUP_NAMES.get(last.next_stage, (text["complete"], text["complete"]))[self._language == "zh-Hant"]
            self.result.setText(text["passed" if last.passed else "failed"].format(name=name, score=last.score,
                next=next_name, n=last.attempt))
        else:
            self.result.setText(text["attempt_count"].format(n=self.session.attempts))

    def _show_stage(self):
        text, session = TEXT[self._language], self.session
        stage = session.stage
        name = GROUP_NAMES.get(stage, (text["complete"], text["complete"]))[self._language == "zh-Hant"]
        self.stage_banner.setText(text["complete"] if session.solved else text["stage"].format(
            index=session.stage_index+1, count=len(session.stages), name=name))
        tasks = ([text["pitch_task"], text["pitch_help"], text["pitch_count"].format(
            done=self._pitch_done(), total=len(self.case.regions))] if stage == "pitch" else
            [text["complete"], text["restored"].format(song=self.case.answers[0])] if session.solved else
            [text["fx_task"].format(name=name), text["fx_help"], text["effect_goal"]])
        for index, label in enumerate(self.clue_labels):
            label.setText(tasks[index] if index < len(tasks) else "")
        self.pitch_count.setText(text["pitch_count"].format(done=self._pitch_done(), total=len(self.case.regions)))

    def _pitch_done(self):
        return sum(abs(r.cents+c) <= PITCH_STAGE_TOLERANCE_CENTS for r, c in zip(self.case.regions, self.session.settings.corrections))

    def _select_region(self, index):
        if index != self._pitch_index and hasattr(self, "busy"):
            self._invalidate()
        self._pitch_index = index
        if hasattr(self, "effects_editor"):
            self._lock()

    def _goto_stage(self):
        if self.session.solved:
            return
        stage = self.session.stage
        device = stage if stage in ("delay", "reverb") else "synth"
        if hasattr(self, "present_device"):
            self.present_device(device)
        self.tabs.setCurrentIndex(0 if stage == "pitch" else 1)
        self.device_requested.emit(device)

    def _lock(self):
        solved = self.session.solved
        for widget in (self.submit_button, self.goto_button, self.play_current, self.play_evidence, self.check_repair_button):
            widget.setEnabled(not solved)
        pitch = self.session.stage == "pitch"
        self.pitch_editor.set_editable(pitch)
        self.effects_editor.set_stage(self.session.stage if not solved else None)
        self.tabs.setTabVisible(0, pitch)
        self.tabs.setTabVisible(1, self.session.stage in ("filter", "delay", "reverb"))
        self.effects_editor.show_groups({self.session.stage})
        if not hasattr(self, "device_kind"):
            self.tabs.setCurrentIndex(2 if solved else 0 if pitch else 1)
        self.reveal_button.setVisible(solved)
        for widget in (self.range_start, self.range_end, self.loop_preview, self.ab_version_button,
                       self.pin_version_button, self.restore_version_button):
            widget.setEnabled(not solved)
        self.note_range_button.setEnabled(pitch)
        if hasattr(self, 'edit_bar'):
            self.edit_bar.refresh()

    def _invalidate(self):
        self._revision = None
        self.renderer.cancel()
        self._audition_jobs, self._audition_items = [], []
        self.busy.hide()
        self.player.stop(immediate=True)

    def _controls_changed(self, *_):
        if self._initializing or self._closed or self.session.solved:
            return
        self._invalidate()
        estimates = replace_parameters(SoundSettings(), self.effects_editor.values()).effects
        try:
            self.session.settings = MusicSettings(self.pitch_editor.corrections, RepairSettings(estimates)).validate(self.case)
        except ValueError:
            self._sync_controls()
            self._status("locked")
            return
        self._repair_stale = True
        self.edit_bar.record(self.session.settings)
        self.comparison_feedback.setText('設定已修改；檢查後更新與上次的進度差異。' if self._language == 'zh-Hant' else
                                         'Edited; check to update progress against your previous check.')
        self._show_repair()
        self._show_stage()
        self._status("updated")
        self._save()

    def _check_repair(self):
        if self._closed or self.session.solved:
            return
        self._repair_report = self.session.report()
        self._update_comparison()
        self._repair_stale = False
        self._show_repair()
        if self.session.stage == "pitch":
            module = self._repair_report.modules[0]
            if self._pitch_done() < len(self.case.regions):
                pending = max(range(len(self.case.regions)), key=lambda i: abs(self.case.regions[i].cents+self.session.settings.corrections[i]))
                self.pitch_editor.select_region(pending)
            self.stage_hint.setText(TEXT[self._language]["ready_submit"] if self._pitch_done() == len(self.case.regions) else module.hint(self._language))

    def _help_and_focus(self):
        self._check_repair();self._goto_stage()

    def _show_repair(self):
        from .investigation_feedback import guidance,device_for
        self._show_submission_feedback()
        text = TEXT[self._language]
        if self._repair_stale or self._repair_report is None:
            guidance(self).show_targets()
            message = text["repair_stale" if self._repair_stale else "repair_pending"]
            self.repair_result.setText(message)
            self.stage_hint.setText(message)
            return
        current = next((module for module in self._repair_report.modules if module.group == self.session.stage), None)
        keys=();extra=();device=''
        if current and current.issue not in ('matched','inactive'):
            if current.group=='pitch':extra=(self.pitch_editor,);device='synth'
            else:
                key=f'{current.group}_enabled' if current.issue=='off' else 'filter_mode' if current.issue=='mode' else current.issue
                keys=(key,);device=device_for(key)
        guidance(self).show_targets(self.effects_editor,keys,device,extra)
        lines = [text["repair_total"].format(score=100*current.fraction if current else 100), text["repair_pending"]]
        for group in self.session.stages:
            module = next(item for item in self._repair_report.modules if item.group == group)
            name = GROUP_NAMES[module.group][self._language == "zh-Hant"]
            if module.group in self.session.completed:
                lines.append(f"{name} · {text['done']}")
            elif module.group != self.session.stage:
                lines.append(f"{name} · {text['future']}")
            else:
                lines.append(f"{name} · {100 * module.fraction:.1f} / 100\n{module.hint(self._language)}")
                if module.group == "pitch":
                    self.stage_hint.setText(text["ready_submit"] if self._pitch_done() == len(self.case.regions) else module.hint(self._language))
                else:
                    self._status("repair_hint")
        self.repair_result.setText("\n\n".join(lines))

    def _play_evidence(self):
        if self._closed or self.session.solved:
            return
        self._invalidate()
        from ..game.music_repair import initial_estimates
        settings = MusicSettings((0,)*len(self.case.regions), RepairSettings(initial_estimates()))
        self._start_audition([(settings, 'evidence')])

    def _play_current(self):
        if self._closed or self.session.solved:
            return
        self._start_audition([(self.session.render_settings(), 'reconstruction')], loop=self.loop_preview.isChecked())

    def _selection(self):
        start, end = self.range_start.value(), self.range_end.value()
        if end-start < .1:
            raise ValueError('Select at least 0.1 seconds / 請選擇至少 0.1 秒')
        # Full preview includes its effect tail; a selected range crops only listening audio.
        return None if start == 0 and end == self.case.seconds else (start, end)

    def _range_changed(self):
        self._invalidate()

    def _use_note_range(self):
        note = self.pitch_map.editable_notes[self._pitch_index]
        self.range_start.setValue(max(0, note.start_seconds-.12))
        self.range_end.setValue(min(self.case.seconds, note.end_seconds+.12))

    def _start_audition(self, jobs, *, loop=False):
        self._invalidate()
        try:
            self._audition_selection = self._selection()
            self._audition_loop = loop
            self._audition_jobs = list(jobs)
            self.busy.show()
            self._status('generating')
            self._next_audition()
        except (OSError, ValueError, RuntimeError) as error:
            self._invalidate()
            self._status('error', message=str(error))

    def _next_audition(self):
        settings, self._pending_label = self._audition_jobs.pop(0)
        self._revision = self.renderer.prepare(self.case, settings, selection=self._audition_selection)

    def _play_versions(self):
        if not self.session.solved:
            self._start_audition([(self._reference_render, 'before'), (self.session.render_settings(), 'after')])

    def _play_region(self):
        if self._closed or self.session.stage != "pitch":
            return
        self._invalidate()
        self.busy.show()
        self._status("generating")
        self._pending_label = "region"
        self._revision = self.renderer.prepare(self.case, self.session.render_settings(), region_index=self._pitch_index)

    def _ready(self, revision, preview):
        if self._closed or self.session.solved or revision != self._revision:
            return
        self._revision = None
        try:
            if self._pending_label == 'region':
                self.busy.hide()
                self.player.play([PlaybackItem(preview.listening_path, 'region', loop=self.loop_preview.isChecked())])
                return
            self._audition_items.append(PlaybackItem(preview.listening_path, self._pending_label,
                                                     loop=self._audition_loop))
            if self._audition_jobs:
                self._next_audition()
            else:
                self.busy.hide()
                self.player.play(self._audition_items)
                self._audition_items = []
        except (OSError, ValueError, RuntimeError) as error:
            self._invalidate()
            self._status('error', message=str(error))

    def _failed(self, revision, message):
        if self._closed or revision != self._revision:
            return
        self._revision = None
        self._audition_jobs, self._audition_items = [], []
        self.busy.hide()
        self._status("error", message=message)

    def _submit(self):
        if self._closed or self.session.solved:
            return
        self._invalidate()
        self._update_comparison()
        result = self.session.submit()
        from .investigation_feedback import ScoreSnapshot
        current=ScoreSnapshot(result.score,{result.stage:result.score},'music:'+result.stage,self.session.attempts)
        previous=self._submission_snapshots.get(result.stage)
        # Other stages can intervene; consecutive means consecutive submissions
        # within this step, not an unrelated global attempt number.
        if previous is not None:
            from dataclasses import replace
            previous=replace(previous,number=current.number-1)
        self._submitted_feedback=(current,previous,result.stage)
        self._submission_snapshots[result.stage]=current
        if result.passed:
            self.edit_bar.reset(self.session.settings)
            self._reset_comparison()
        self._repair_report = self.session.report()
        self._repair_stale = False
        self._result_kind = "solved" if self.session.solved else None
        self._show_result()
        self._show_stage()
        self._show_repair()
        self._save()
        self._lock()
        if result.newly_solved:
            self._play_reveal()
            self.case_completed.emit()
        elif result.passed:
            self._goto_stage()
        else:
            self._check_repair()

    def _play_reveal(self):
        if self._closed or not self.session.solved:
            return
        self._invalidate()
        try:
            self.player.play([PlaybackItem(self.case.source, "reveal", loop=True, gain=self.case.reveal_gain)])
        except (OSError, ValueError, RuntimeError) as error:
            self._status("error", message=str(error))

    def _player_state(self, state, label):
        if self._closed:
            return
        if state in {"playing", "loading"}:
            if label == "reveal":
                self._status("full")
            elif label == "region":
                self._status("region_playing")
            else:
                names = {'before': '之前版本' if self._language == 'zh-Hant' else 'Before version',
                         'after': '目前版本' if self._language == 'zh-Hant' else 'Current version'}
                key = 'evidence' if label == 'evidence' else 'current'
                self._status('playing', label=names.get(label, TEXT[self._language][key]))

    def stop(self):
        if not self._closed:
            self.pitch_editor.roll.cancel_drag()
            self._invalidate()
            self._status("stopped")

    def _restart(self):
        self.stop()
        self._submission_snapshots={};self._submitted_feedback=None
        self.session.restart()
        self.edit_bar.reset(self.session.settings)
        self._reset_comparison()
        self._sync_controls()
        self.pitch_editor.select_region(0)
        self._result_kind = None
        self._repair_report = None
        self._repair_stale = False
        self._show_repair()
        self._status("idle")
        self._show_result()
        self._show_stage()
        self._lock()
        self._goto_stage()
        self._save()

    def _show_submission_feedback(self):
        if not hasattr(self,'submission_feedback'):return
        if self._submitted_feedback is None:
            self.submission_feedback.show_scores();return
        current,previous,stage=self._submitted_feedback
        zh=self._language=='zh-Hant'
        name=GROUP_NAMES[stage][zh]
        self.submission_feedback.show_scores(current,previous,language=self._language,labels={stage:name},rounding='round')
        text=(f'上次提交 · {name}\n' if zh else f'Last submission · {name}\n')+self.submission_feedback.text()
        self.submission_feedback.setText(text);self.submission_feedback.setToolTip(text)

    def _reset_comparison(self):
        self._reference_settings = self.session.settings
        self._reference_render = self.session.render_settings()
        self._last_check_score = self._step_score()
        self._last_checked_settings = self.session.settings
        self._comparison_delta = None
        if hasattr(self, 'comparison_feedback'):
            self._show_comparison()

    def _step_score(self):
        return next((100*m.fraction for m in self.session.report().modules if m.group == self.session.stage), 100.)

    def _update_comparison(self):
        score = self._step_score()
        self._comparison_delta = score - self._last_check_score
        self._last_check_score = score
        self._last_checked_settings = self.session.settings
        self._show_comparison()

    def _show_comparison(self):
        zh = self._language == 'zh-Hant'
        if self.session.settings != self._last_checked_settings:
            text = '設定已修改；檢查後更新與上次的進度差異。' if zh else 'Edited; check to update progress against your previous check.'
        elif self._comparison_delta is None:
            text = '已記住本步驟的初始版本，可前後試聽。' if zh else 'Step baseline remembered; compare before and now.'
        else:
            delta = self._comparison_delta
            word = ('更接近' if delta > .05 else '更遠' if delta < -.05 else '接近程度相同') if zh else (
                'closer' if delta > .05 else 'further away' if delta < -.05 else 'unchanged')
            text = (f'目前 {self._last_check_score:.1f} / 100；比上次檢查{word}（{delta:+.1f} 分）。' if zh else
                    f'Current {self._last_check_score:.1f} / 100; {word} than the previous check ({delta:+.1f} points).')
        self.comparison_feedback.setText(text)

    def _pin_version(self):
        if self.session.solved:
            return
        self._reference_settings, self._reference_render = self.session.settings, self.session.render_settings()
        self.comparison_feedback.setText('已記住目前版本。' if self._language == 'zh-Hant' else 'Current version remembered.')

    def _restore_edit(self, settings):
        if self.session.solved:
            return
        self.stop()
        self.session.settings = settings
        self.edit_bar.record(settings, merge=False)
        self._sync_controls()
        self._repair_stale = True
        self._show_comparison()
        self._show_repair()
        self._show_stage()
        self._status('updated')
        self._save()

    def _sync_controls(self):
        self._initializing = True
        self.pitch_editor.set_corrections(self.session.settings.corrections)
        self.effects_editor.set_settings(SoundSettings(effects=self.session.settings.repair.estimates))
        self._initializing = False

    def _change_language(self):
        self._language = self.language.currentData()
        self._translate()
        self._save()

    def _volume_changed(self, value):
        self._volume = value / 100
        self.player.set_volume(self._volume)
        self._save()

    def _show_save_warning(self):
        text = TEXT[self._language]
        message = (text["save_error"].format(message=self._save_problem) if self._save_problem else
                   text["backup"] if self._backup else text["migration"] if self._migration_backup else "")
        self.save_warning.setText(message)
        self.save_warning.setVisible(bool(message))

    def _save(self):
        if self._initializing or self._save_blocked:
            return
        try:
            atomic_json_write(self.store.path, {"schema_version": 1, "session": self.session.to_dict(),
                "language": self._language, "volume": self._volume})
            self._save_problem = None
        except (OSError, ValueError) as error:
            self._save_problem = str(error)
        self._show_save_warning()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowDeactivate and not self._closed and not self.session.solved:
            QTimer.singleShot(0, self._check_focus)

    def _check_focus(self):
        popup = QApplication.activePopupWidget()
        if not self._closed and not self.session.solved and not self.isActiveWindow() and not (popup and self.isAncestorOf(popup)):
            self.stop()

    def closeEvent(self, event):
        if not self._closed:
            self._invalidate()
            self._save()
            self._closed = True
            self.player.close()
            self.renderer.close()
        event.accept()
