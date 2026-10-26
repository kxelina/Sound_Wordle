"""Playable W01: build a hidden sound from clues, with unlimited submissions."""

from pathlib import Path
import math

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QProgressBar, QPushButton, QSlider, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView)

from ..audio.sc_client import ROOT
from ..audio.playback import AudioPlayer, PlaybackItem
from ..audio.preview import PreviewRenderer
from ..game.hidden_sound import (HiddenSession, STAGES, assess, lesson, load_hidden_case,
    load_hidden_session, save_hidden_session, settings_from_parameters)
from ..game.parameters import PARAMETERS
from ..game.storage import SessionStore
from .hardware import PlaybackDeck
from .parameter_editor import ParameterEditor


TEXT = {
    "en": {
        "title": "Sound Wordle · W01 · The Corridor Signal", "notebook": "Witness notebook",
        "story": '“It started quickly, sounded bright, then stopped neatly. A quieter repeat followed a moment later.”',
        "rules": "Build from a pure tone · unlimited submissions · hints are free. The target stays hidden until all three requirements pass.",
        "stages": ("1 · Short outline", "2 · Bright colour", "3 · Gentle echo"),
        "goals": ("Quick attack and a short release", "Add some upper-harmonic energy", "A short, quieter echo"),
        "editor": "Build your sound", "submit": "Submit this version", "hint": "More help (free)",
        "lesson": "Hear this concept", "next": "Go to the suggested device", "reset": "Start over",
        "history": "Notebook · last 30 submissions", "restore": "Restore selected", "listen_history": "Hear selected",
        "columns": ("Version", "Progress", "Requirements"), "current": "Play my sound", "reference": "Target · locked",
        "reference_open": "Play hidden target", "ab": "A/B · target → mine", "stop": "Stop · Esc",
        "unscored": "No submission yet · no attempt limit", "score": "Version {n} · progress {score} / 100",
        "outdated": "Settings changed; the score above belongs to the last submission.",
        "stage": "Stage {n}/3 · {name}", "locked": "Finish the earlier stage, then submit to unlock these controls.",
        "unused": "This prototype uses Synthesizer and Delay. Filter and Reverb stay off.",
        "initial": "Listen to your pure tone, adjust Attack / Release, then submit. Ask for help whenever needed.",
        "submitted": "Notebook updated. All three requirements must pass; this is not a perceptual similarity percentage.",
        "ready_stage": "This part meets its requirements. Submit to record it and unlock the next stage.",
        "solved": "Signal reconstructed! The hidden target and A/B are unlocked. Different valid settings can pass.",
        "practice": "Practice · the target was already unlocked. You can keep experimenting.",
        "hint_level": "Help {tier}/3 · {message}", "generating": "Preparing audio… first playback may take a moment.",
        "playing": "Playing: {label}", "stopped": "Stopped.", "hidden": "The target unlocks only after all three requirements pass.",
        "error": "Audio error: {message}", "saved_bad": "Unreadable W01 progress was backed up; a fresh prototype has started.",
        "save_error": "W01 progress could not be saved; the original file has been retained.",
        "lesson_note": "Teaching pair: {pair}. These are generic A3 examples, not the hidden A4 target.",
        "pairs": ("short release → long release", "pure tone → upper harmonics", "dry → gentle echo"),
        "status_words": ("Met", "Close", "Not yet", "Locked"),
        "machines": ("Synthesizer", "Delay", "Notebook"),
    },
    "zh-Hant": {
        "title": "Sound Wordle · W01 · 走廊裡的電子信號", "notebook": "證人口供與調查筆記",
        "story": "「聲音很快響起來，有點尖亮，收尾很利落。過了一小會兒，又有一個更輕的重複聲。」",
        "rules": "從純音開始製作 · 提交不限次 · 提示免費。三項線索均達標後才揭曉目標聲音。",
        "stages": ("1 · 短促起落", "2 · 明亮音色", "3 · 輕微回聲"),
        "goals": ("迅速起音，短促收尾", "加入適量高次諧波能量", "稍後出現較輕的短回聲"),
        "editor": "製作你的聲音", "submit": "提交目前版本", "hint": "再給我一點幫助（免費）",
        "lesson": "聽聽這個概念", "next": "前往建議的設備", "reset": "重新開始",
        "history": "調查記錄 · 最近 30 次提交", "restore": "恢復選中版本", "listen_history": "試聽選中版本",
        "columns": ("版本", "進度", "線索達標"), "current": "試聽我的聲音", "reference": "目標音 · 未揭曉",
        "reference_open": "播放隱藏目標", "ab": "A/B · 目標 → 我的聲音", "stop": "停止 · Esc",
        "unscored": "尚未提交 · 不限提交次數", "score": "第 {n} 版 · 重建進度 {score} / 100",
        "outdated": "設定已修改；以上分數屬於上次提交。",
        "stage": "階段 {n}/3 · {name}", "locked": "先完成前一階段並提交，才會開放這些控制項。",
        "unused": "本測試關使用合成器與 Delay；Filter、Reverb 保持關閉。",
        "initial": "先試聽純音，再調整 Attack／Release 並提交。卡住時隨時領取幫助。",
        "submitted": "調查筆記已更新。三項線索均需達標；分數不是人耳相似度百分比。",
        "ready_stage": "這一部分已符合要求；提交後記錄成果，並開放下一階段。",
        "solved": "信號重建完成！已解鎖隱藏目標與 A/B，不同的合理設定也可以通關。",
        "practice": "練習中 · 目標已曾揭曉，可以繼續自由實驗。",
        "hint_level": "第 {tier}/3 層幫助 · {message}", "generating": "正在準備聲音……首次試聽可能需要稍候。",
        "playing": "正在播放：{label}", "stopped": "已停止。", "hidden": "三項線索均達標後才會解鎖目標聲音。",
        "error": "音訊錯誤：{message}", "saved_bad": "無法讀取的 W01 進度已備份，目前開始新的測試關。",
        "save_error": "無法儲存 W01 進度，原檔已保留。",
        "lesson_note": "教學對比：{pair}。這是普通 A3 教學音，不是隱藏的 A4 目標。",
        "pairs": ("短尾音 → 長尾音", "純音 → 加入高次諧波", "乾聲 → 輕微回聲"),
        "status_words": ("達標", "接近", "未達標", "未開放"),
        "machines": ("合成器", "回聲設備", "調查筆記"),
    },
}

# Diagnosis, machine, then action. No exact hidden target values are exposed.
CLUES = {
    "attack_high": (("The start swells too slowly.", "起音上升得太慢。"),
        ("Use the synthesizer's ADSR section.", "檢查合成器的 ADSR 區。"),
        ("Turn Attack down, then listen to the beginning again.", "降低 Attack，再聽聲音的開頭。")),
    "release_high": (("The sound lingers too long after the note ends.", "音符結束後，聲音仍拖得太久。"),
        ("Use Release in the synthesizer's ADSR section.", "檢查合成器 ADSR 區的 Release。"),
        ("Turn Release down to make the ending more decisive.", "降低 Release，讓收尾更利落。")),
    "brightness_low": (("The pure tone needs a brighter edge.", "目前純音需要更明亮的邊緣。"),
        ("Open the synthesizer's Harmonics section.", "打開合成器的諧波區。"),
        ("Raise one or more of H2–H4. Keep some balance with H1.", "提高 H2–H4 中一個或多個推桿，保留與 H1 的平衡。")),
    "brightness_high": (("The upper harmonics dominate too strongly.", "高次諧波太突出。"),
        ("Check H2–H4 on the synthesizer.", "檢查合成器的 H2–H4。"),
        ("Lower some of H2–H4 and listen again.", "降低部分 H2–H4，再次試聽。")),
    "echo_low": (("The witness described an echo; yours is still dry.", "口供提到回聲，目前仍缺少可聽到的回聲。"),
        ("Go to the Delay processor.", "前往 Delay 回聲處理器。"),
        ("Switch Delay on and give Wet mix some level.", "開啟 Delay，並給濕聲比例一點音量。")),
    "delay_time_low": (("The repeat follows too quickly.", "重複聲跟得太緊。"),
        ("Check Echo spacing on the Delay processor.", "檢查 Delay 的回聲間隔。"),
        ("Increase Echo spacing a little.", "稍微增加回聲間隔。")),
    "delay_time_high": (("The repeat arrives too late.", "重複聲來得太遲。"),
        ("Check Echo spacing on the Delay processor.", "檢查 Delay 的回聲間隔。"),
        ("Reduce Echo spacing a little.", "稍微縮短回聲間隔。")),
    "delay_decay_high": (("The echo keeps ringing for too long.", "回聲持續得太久。"),
        ("Check Decay time on the Delay processor.", "檢查 Delay 的衰減時間。"),
        ("Reduce Delay's Decay time; leave the dry Release alone for now.", "縮短 Delay 的衰減時間，暫時不用改乾聲的 Release。")),
    "delay_mix_low": (("The repeat is too faint.", "重複聲太輕。"),
        ("Check Wet mix on the Delay processor.", "檢查 Delay 的濕聲比例。"),
        ("Raise Wet mix so the repeat can be heard.", "提高濕聲比例，讓重複聲可以被聽見。")),
    "delay_mix_high": (("The repeat is too loud beside the first sound.", "重複聲相對原聲太響。"),
        ("Check Wet mix on the Delay processor.", "檢查 Delay 的濕聲比例。"),
        ("Lower Wet mix to leave a quieter repeat.", "降低濕聲比例，保留較輕的重複聲。")),
}


class HiddenSoundWindow(QMainWindow):
    case_completed = Signal()
    device_requested = Signal(str)

    def __init__(self, *, case=None, save_path=None, player=None, renderer=None,
                 language="en", volume=.35, embedded=False):
        super().__init__()
        self.case = case or load_hidden_case()
        self.save_path = Path(save_path or ROOT / "userdata/wordle/W01.json")
        self._language, self.embedded = language, embedded
        self._initial_volume = volume
        self._closed = self._save_blocked = False
        self._warning = ""
        self._revision = self._armed = None
        self.device_kind = "synth"
        self._preferred_group = "envelope"
        try:
            self.session = load_hidden_session(self.save_path)
        except (OSError, ValueError, TypeError, KeyError):
            self.session = HiddenSession()
            try:
                SessionStore(self.save_path).preserve_invalid()
                self._warning = "saved_bad"
            except OSError:
                self._warning, self._save_blocked = "save_error", True
        self.player = player or AudioPlayer(self)
        self.renderer = renderer or PreviewRenderer(self)
        self._build()
        self.editor.set_settings(self.session.current)
        from .edit_history import EditHistoryBar
        self.edit_bar = EditHistoryBar(self, self.session.current, self._restore_edit,
                                       enabled=lambda: not self._closed)
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
        return TEXT[self._language][key]

    def _label(self):
        label = QLabel()
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        return label

    def _build(self):
        body = QWidget()
        body.setObjectName("wordle_body")
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)
        top = QHBoxLayout()
        self.title = self._label()
        self.title.setStyleSheet("font-size: 19px; color: #efd6a0;")
        top.addWidget(self.title, 1)
        self.title.setVisible(not self.embedded)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("繁體中文", "zh-Hant")
        self.language.setCurrentIndex(self._language == "zh-Hant")
        self.language.currentIndexChanged.connect(self._change_language)
        top.addWidget(self.language)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(self._initial_volume * 100))
        self.volume.valueChanged.connect(lambda value: self.player.set_volume(value / 100))
        self.volume.setMaximumWidth(110)
        top.addWidget(self.volume)
        self.language.setVisible(not self.embedded)
        self.volume.setVisible(not self.embedded)
        layout.addLayout(top)
        self.rules, self.stage_label = self._label(), self._label()
        self.rules.setStyleSheet("color: #bfb79f; font-size: 13px;")
        layout.addWidget(self.rules)
        layout.addWidget(self.stage_label)
        self.navigation = QWidget()
        navigation = QHBoxLayout(self.navigation)
        navigation.setContentsMargins(0, 0, 0, 0)
        self.device_buttons = {}
        for device in ("synth", "delay", "analyzer"):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, key=device: self.present_device(key))
            navigation.addWidget(button)
            self.device_buttons[device] = button
        self.navigation.setVisible(not self.embedded)
        layout.addWidget(self.navigation)
        columns = QHBoxLayout()
        self.notebook, self.machine = QGroupBox(), QGroupBox()
        self.notebook.setMaximumWidth(410)
        left, right = QVBoxLayout(self.notebook), QVBoxLayout(self.machine)
        left.setSpacing(7)
        self.story, self.score, self.cards = self._label(), self._label(), self._label()
        self.stale = self._label()
        self.stale.setStyleSheet("font-size: 12px; color: #bfb79f;")
        self.score.setObjectName("wordle_score")
        self.score.setStyleSheet("font-size: 19px; color: #f1d59a;")
        self.cards.setObjectName("wordle_requirements")
        for label in (self.story, self.score, self.stale, self.cards):
            left.addWidget(label)
        left.addStretch()
        self.play_reference, self.play_current, self.stop_button, self.play_ab = (QPushButton() for _ in range(4))
        self.play_reference.clicked.connect(lambda: self._prepare("reference"))
        self.play_current.clicked.connect(lambda: self._prepare("current"))
        self.play_ab.clicked.connect(lambda: self._prepare("ab"))
        self.stop_button.clicked.connect(self.stop)
        self.deck = PlaybackDeck(self.play_reference, self.play_current, self.stop_button, self.play_ab, compact=True)
        left.addWidget(self.deck)
        self.feedback = self._label()
        self.feedback.setObjectName("wordle_hint")
        right.addWidget(self.feedback)
        hints = QHBoxLayout()
        self.hint_button, self.lesson_button = QPushButton(), QPushButton()
        self.hint_button.clicked.connect(self._hint)
        self.lesson_button.clicked.connect(lambda: self._prepare("lesson"))
        hints.addWidget(self.hint_button)
        hints.addWidget(self.lesson_button)
        right.addLayout(hints)
        self.editor = ParameterEditor(self.case)
        self.editor.use_hardware_controls()
        self.controls = self.editor.controls
        self.editor.changed.connect(self._parameters_changed)
        right.addWidget(self.editor, 1)
        self.locked = self._label()
        right.addWidget(self.locked)
        self.goto_button = QPushButton()
        self.goto_button.clicked.connect(self._goto_suggested)
        right.addWidget(self.goto_button)
        self.history = QTableWidget(0, 3)
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.verticalHeader().hide()
        right.addWidget(self.history, 1)
        history_actions = QHBoxLayout()
        self.restore_button, self.history_play = QPushButton(), QPushButton()
        self.restore_button.clicked.connect(self._restore)
        self.history_play.clicked.connect(self._hear_history)
        history_actions.addWidget(self.restore_button)
        history_actions.addWidget(self.history_play)
        right.addLayout(history_actions)
        columns.addWidget(self.notebook, 4)
        columns.addWidget(self.machine, 7)
        layout.addLayout(columns, 1)
        buttons = QHBoxLayout()
        self.submit_button, self.history_button, self.reset_button = QPushButton(), QPushButton(), QPushButton()
        self.submit_button.setObjectName("wordle_submit")
        self.submit_button.clicked.connect(self._submit)
        self.history_button.clicked.connect(lambda: self.device_requested.emit("analyzer"))
        self.reset_button.clicked.connect(self._restart)
        for button in (self.submit_button, self.history_button, self.reset_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedHeight(4)
        self.busy.hide()
        layout.addWidget(self.busy)
        self.status, self.save_warning = self._label(), self._label()
        self.status.setStyleSheet("font-size: 13px; color: #bfb79f;")
        layout.addWidget(self.status)
        layout.addWidget(self.save_warning)
        self.shortcut = QShortcut(QKeySequence("Escape"), self)
        self.shortcut.activated.connect(self.stop)
        self.shortcut.setEnabled(not self.embedded)
        self.resize(1180, 720)

    def _change_language(self, index):
        self._language = self.language.itemData(index)
        self._translate()

    def _translate(self):
        from .hover_help import apply_window_help
        self.setWindowTitle(self.t("title"))
        self.title.setText(self.t("title"))
        self.rules.setText(self.t("rules"))
        self.notebook.setTitle(self.case.title[self._language] if self.embedded else self.t("notebook"))
        self.machine.setTitle(self.t("editor"))
        self.story.setText(self.t("story"))
        for button, key in ((self.play_current, "current"), (self.play_ab, "ab"), (self.stop_button, "stop"),
            (self.submit_button, "submit"), (self.history_button, "history"), (self.reset_button, "reset"),
            (self.hint_button, "hint"), (self.lesson_button, "lesson"), (self.goto_button, "next"),
            (self.restore_button, "restore"), (self.history_play, "listen_history")):
            button.setText(self.t(key))
        self.editor.translate(self._language)
        for button, name in zip(self.device_buttons.values(), self.t("machines")):
            button.setText(name)
        self.deck.translate(self._language)
        self.status.setText(self.t("initial"))
        self._refresh(history=True)
        apply_window_help(self, "hidden", self._language)

    def _refresh(self, *, history=False):
        s = self.session
        self.stage_label.setText(self.t("stage").format(n=s.focus + 1, name=self.t("stages")[s.focus].split("·", 1)[1].strip()))
        if not s.records:
            self.score.setText(self.t("unscored"))
            self.cards.setText("\n".join(self.t("goals")))
        else:
            result = assess(settings_from_parameters(s.records[-1]["parameters"]))
            shown = math.floor(result.total * 10) / 10
            self.score.setText(self.t("score").format(n=s.attempts, score=f"{shown:.1f}"))
            lines = []
            for i, goal in enumerate(self.t("goals")):
                word = self.t("status_words")[3 if i > s.unlocked else 0 if result.passed[i] else 1 if result.scores[i] >= 60 else 2]
                lines.append(f"{word} · {goal}")
            self.cards.setText("\n".join(lines))
        self.stale.setText(self.t("outdated"))
        self.stale.setVisible(bool(s.records) and not s.current_is_submitted)
        self.play_reference.setText(self.t("reference_open" if s.solved else "reference"))
        self.play_reference.setEnabled(s.solved)
        self.play_ab.setEnabled(s.solved)
        self.save_warning.setText(self.t(self._warning) if self._warning else "")
        self.save_warning.setVisible(bool(self._warning))
        self._show_clue()
        if history:
            selected = self.history.currentRow()
            self.history.setHorizontalHeaderLabels(self.t("columns"))
            self.history.setRowCount(len(s.records))
            for row, record in enumerate(s.records):
                result = assess(settings_from_parameters(record["parameters"]))
                for column, value in enumerate((str(record["number"]), f"{result.total:.1f}", f"{sum(result.passed)}/3")):
                    self.history.setItem(row, column, QTableWidgetItem(value))
            if s.records:
                self.history.setCurrentCell(min(selected, len(s.records)-1) if selected >= 0 else len(s.records)-1, 0)
        self.restore_button.setEnabled(bool(s.records))
        self.history_play.setEnabled(bool(s.records))
        self.present_device(self.device_kind)

    def _suggested_device(self):
        return "delay" if self.session.focus == 2 else "synth"

    def _goto_suggested(self):
        self._preferred_group = "envelope" if self.session.focus == 0 else "harmonics"
        self.device_requested.emit(self._suggested_device())

    def present_device(self, device):
        self.device_kind = device
        for key, button in self.device_buttons.items():
            button.setChecked(key == device)
        groups = ({"envelope"} | ({"harmonics"} if self.session.unlocked >= 1 else set())) if device == "synth" else {"delay"} if device == "delay" and self.session.unlocked >= 2 else set()
        self.editor.show_groups(groups)
        self.editor.setVisible(bool(groups))
        self.editor.set_locked(False)
        allowed = sum(STAGES[:self.session.unlocked+1], ())
        for key in self.controls:
            if key not in allowed:
                self.controls[key].setEnabled(False)
                if key in self.editor.sliders:
                    self.editor.sliders[key].setEnabled(False)
                if key in self.editor.knobs:
                    self.editor.knobs[key].setEnabled(False)
        if device == "synth" and self._preferred_group in groups:
            self.editor.tabs.setCurrentIndex(self.editor._tab_groups.index(self._preferred_group))
            self._preferred_group = None
        analyzing = device == "analyzer"
        self.history.setVisible(analyzing)
        self.restore_button.setVisible(analyzing)
        self.history_play.setVisible(analyzing)
        self.hint_button.setVisible(not analyzing)
        self.lesson_button.setVisible(not analyzing)
        self.locked.setVisible(not groups and not analyzing)
        self.locked.setText(self.t("locked" if device == "delay" else "unused"))
        self.goto_button.setVisible(not groups or self._suggested_device() != device)

    def _show_clue(self):
        s, result = self.session, assess(self.session.current)
        if all(result.passed) and s.current_is_submitted:
            message = self.t("solved")
        else:
            problem = result.problem(s.focus)
            if problem is None:
                message = self.t("ready_stage")
            else:
                variants = CLUES.get(f"{problem.code}_{problem.direction}")
                tier = s.hints[s.focus]
                message = " ".join(pair[self._language == "zh-Hant"] for pair in variants[:max(1, tier)]) if variants else self.t("initial")
                if tier:
                    message = self.t("hint_level").format(tier=tier, message=message)
            if s.solved:
                message = self.t("practice") + "\n" + message
        self.feedback.setText(message)

    def _parameters_changed(self):
        if self._closed:
            return
        self.stop()
        try:
            self.session.update(self.editor.values())
            self.edit_bar.record(self.session.current)
        except ValueError:
            self.editor.set_settings(self.session.current)
            self.status.setText(self.t("locked"))
        self._refresh()
        self._save()

    def _submit(self):
        was_solved = self.session.solved
        self.stop()
        previous = self.session.unlocked
        result = self.session.submit()
        if self.session.unlocked > previous:
            self._preferred_group = "harmonics"
        self._refresh(history=True)
        self.status.setText(self.t("solved" if all(result.passed) else "submitted"))
        self._save()
        if not was_solved and self.session.solved:
            self.case_completed.emit()

    def _restore_edit(self, settings):
        self.stop()
        from ..game.hidden_sound import parameters
        self.session.update(parameters(settings))
        self.editor.set_settings(self.session.current)
        self._refresh()
        self._save()

    def _hint(self):
        self.session.request_hint()
        self._show_clue()
        self._save()

    def _restore(self):
        index = self.history.currentRow()
        if index >= 0:
            self.stop()
            self.session.restore(index)
            self.edit_bar.record(self.session.current, merge=False)
            self.editor.set_settings(self.session.current)
            self._refresh()
            self._save()

    def _hear_history(self):
        if self.history.currentRow() >= 0:
            self._prepare("history")

    def _restart(self):
        self.stop()
        self.session = HiddenSession(solution=self.session.solution)
        self.edit_bar.reset(self.session.current)
        self.editor.set_settings(self.session.current)
        self._preferred_group = "envelope"
        self._refresh(history=True)
        self._save()

    def _prepare(self, mode):
        if self._closed:
            return
        if mode in ("reference", "ab") and not self.session.solved:
            self.status.setText(self.t("hidden"))
            return
        self.stop()
        if mode == "lesson":
            self._lesson_stage = self.session.focus
            pair, sequence = lesson(self.session.focus)
            requests = {"lesson1": (pair[0], sequence), "lesson2": (pair[1], sequence)}
            self.status.setText(self.t("lesson_note").format(pair=self.t("pairs")[self.session.focus]))
        elif mode == "history":
            row = self.history.currentRow()
            if row < 0:
                return
            requests = {"history": (settings_from_parameters(self.session.records[row]["parameters"]), self.case.sequence)}
        else:
            requests = {key: (settings, self.case.sequence) for key, settings in
                (("target", self.case.reference), ("current", self.session.current))
                if mode == "ab" or key == ("target" if mode == "reference" else "current")}
        self._armed = tuple(requests)
        self.busy.show()
        try:
            self._revision = self.renderer.prepare(requests)
            if mode != "lesson":
                self.status.setText(self.t("generating"))
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
            if label in ("lesson1", "lesson2"):
                self.status.setText(self.t("lesson_note").format(pair=self.t("pairs")[self._lesson_stage]) + f"  ({label[-1]}/2)")
                return
            names = {"current": self.t("current"), "target": self.t("reference_open"),
                     "history": self.t("listen_history"), "lesson1": "1", "lesson2": "2"}
            self.status.setText(self.t("playing").format(label=names.get(label, label)))

    def stop(self):
        self._revision = self._armed = None
        self.renderer.cancel()
        self.player.stop()
        self.busy.hide()
        self.status.setText(self.t("stopped"))

    def _save(self):
        if self._save_blocked:
            return
        try:
            save_hidden_session(self.save_path, self.session)
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
