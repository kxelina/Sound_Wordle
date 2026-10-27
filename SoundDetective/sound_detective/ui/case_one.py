"""Data-driven case window; the original T01 entry remains compatible."""

import math

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton, QSlider, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QProgressBar,
    QDialog, QDialogButtonBox, QScrollArea,
)
from PySide6.QtGui import QKeySequence, QShortcut

from .audio_bench import AudioBench
from ..audio.sc_client import ROOT
from ..game.cases import load_case
from ..game.session import SessionState
from ..game.storage import SessionStore
from ..game.parameters import GROUPS, PARAMETERS
from ..game.progress import PROGRESS_VERSION
from ..game.diagnostics import describe_clue, visible_clue_codes
from ..audio.clue_features import DiagnosticContext
from .parameter_editor import ParameterEditor
from .investigation_feedback import SubmissionFeedback,ScoreSnapshot,tone_guidance


TEXT = {
    "en": {
        "title": "Sound Detective — Case 01", "target": "Evidence · reference sound", "current": "Reconstruction",
        "release": "Release (s)", "cutoff": "Low-pass cutoff (Hz)", "locked": "Other sound controls are fixed for this case.",
        "play_a": "Listen to reference", "play_b": "Listen to reconstruction", "play_ab": "A/B · reference → reconstruction",
        "submit": "Submit answer", "stop": "Stop · Esc", "restart": "Restart case", "volume": "Output volume",
        "unscored": "No submissions yet.", "score": "Submission {number} · reconstruction {score} / 100\n{outcome}",
        "legacy_score": "Submission {number} · historical audio match {score} / 100\n{outcome}",
        "passed": "Case solved", "retry": "Keep investigating", "outdated": "Last submitted score · controls have changed.",
        "gate": "A submission scoring at least {threshold:g} unlocks a diagnosis for that answer.",
        "changed": "Submit the new settings to obtain an updated score and diagnosis.", "comparing": "Comparing this answer…",
        "progress": "{phase} · submitted: {attempts} · {seconds:.0f} s", "playing": "Investigation", "practice": "Practice", "solved": "Solved",
        "compared": "Answer compared.", "ready": "Sounds ready to audition.", "idle": "Listen to the reference and start investigating.",
        "history": ["Attempt", "Score / 100", "Diagnosis", "Result"], "yes": "Available", "no": "Locked",
        "review": "Review — reference cutoff: {cutoff:g} Hz; Release: {release:.2f} s.\nYour spectrum {spectrum:.1f} · envelope {envelope:.1f} · tail {tail:.1f}.",
        "first": "First clear preserved: {total:.1f} points, {number} submissions.",
        "note": "Progress measures closeness to target controls, not audio similarity. Equal module weights. Diagnosis {hint:g}+; pass {passing:g}+ and every module {component:g}+.",
        "legacy_note": "Historical audio score preserved. New submissions use reconstruction progress.",
        "backup": "Unreadable progress was backed up. A fresh investigation has started.",
        "save_error": "Progress could not be saved: {message}",
        "duller": "Your answer has less high-frequency energy. Try increasing the cutoff.",
        "brighter": "Your answer has more high-frequency energy. Try reducing the cutoff.",
        "spectrum": "The spectral balance differs. Adjust the low-pass cutoff and listen again.",
        "longer_tail": "Your answer continues after the reference ends. Try a shorter Release.",
        "shorter_tail": "Your answer ends earlier than the reference. Try a longer Release.",
        "envelope": "The volume shape over time differs. Adjust Release and compare again.",
        "close": "No large measured difference remains. Listen to the pair again.",
        "uncertain": "A difference remains, but its adjustment direction is uncertain. Compare the sounds again.",
    },
    "zh-Hant": {
        "title": "Sound Detective — 案件 01", "target": "證物 · 參照聲音", "current": "聲音還原",
        "release": "Release（秒）", "cutoff": "低通截止頻率（Hz）", "locked": "此案件的其他聲音控制項已固定。",
        "play_a": "聆聽參照", "play_b": "聆聽還原聲音", "play_ab": "A/B · 參照 → 還原聲音",
        "submit": "提交答案", "stop": "停止 · Esc", "restart": "重新挑戰", "volume": "輸出音量",
        "unscored": "尚未提交答案。", "score": "第 {number} 次提交 · 還原進度 {score} / 100\n{outcome}",
        "legacy_score": "第 {number} 次提交 · 歷史音訊匹配分數 {score} / 100\n{outcome}",
        "passed": "案件已解決", "retry": "繼續調查", "outdated": "上次提交的分數 · 控制項已修改。",
        "gate": "本次提交達到 {threshold:g} 分，才會顯示該答案的診斷。",
        "changed": "請提交新設定，取得更新的分數及診斷。", "comparing": "正在比較本次答案…",
        "progress": "{phase} · 已提交 {attempts} 次 · {seconds:.0f} 秒", "playing": "調查中", "practice": "練習", "solved": "已解決",
        "compared": "本次答案已比較。", "ready": "聲音已準備好，可開始試聽。", "idle": "聆聽參照聲音，開始調查。",
        "history": ["提交", "分數 / 100", "診斷", "結果"], "yes": "可查看", "no": "未開放",
        "review": "復盤 — 參照截止頻率：{cutoff:g} Hz；Release：{release:.2f} 秒。\n本次頻譜 {spectrum:.1f} · 包絡 {envelope:.1f} · 尾音 {tail:.1f}。",
        "first": "首次通關紀錄已保留：{total:.1f} 分，提交 {number} 次。",
        "note": "進度根據目標控制項的接近程度計算，並非音訊相似度；各模組同權。{hint:g} 分開放診斷；通關需總分至少 {passing:g}、每個模組至少 {component:g}。",
        "legacy_note": "歷史音訊成績已保留；新提交使用還原進度。",
        "backup": "無法讀取的進度已備份，目前開始新的調查。",
        "save_error": "無法儲存進度：{message}",
        "duller": "目前答案的高頻比參照少，可嘗試提高截止頻率。",
        "brighter": "目前答案的高頻比參照多，可嘗試降低截止頻率。",
        "spectrum": "頻譜分布有差異；請調整低通截止頻率，再試聽比較。",
        "longer_tail": "參照結束後，目前答案仍持續；可嘗試縮短 Release。",
        "shorter_tail": "目前答案比參照更早結束；可嘗試延長 Release。",
        "envelope": "音量隨時間的形狀有差異；請調整 Release 再比較。",
        "close": "未測到明顯差異，可再次比較兩段聲音。",
        "uncertain": "仍有差異，但無法可靠判斷調整方向；請再次試聽比較。",
    },
}


def display_score(value):
    # Truncate rather than round across a gate (74.99 must not display 75.0).
    return f"{math.floor(value * 10) / 10:.1f}"


class CaseWindow(AudioBench):
    case_completed = Signal()
    review_requested = Signal()
    def __init__(self, *, case=None, save_path=None, player=None, renderer=None):
        self._initializing = True
        self._load_progress(case or load_case(ROOT / "content/cases/T01.json"), save_path)
        self._submission_token = None
        super().__init__(player=player, renderer=renderer)
        self.resize(1280, 720)
        self.setMinimumSize(1088, 660)
        self._sync_controls()
        self.language.blockSignals(True)
        self.language.setCurrentIndex(0 if self.session.language == "en" else 1)
        self.language.blockSignals(False)
        self._language = self.session.language
        self.volume.setValue(round(self.session.volume * 100))
        self.player.set_volume(self.session.volume)
        self._initializing = False
        from .edit_history import EditHistoryBar
        self.edit_bar = EditHistoryBar(self, self.session.current, self._restore_edit,
            enabled=lambda: not self._closed and not self.session.solved and self._submission_token is None)
        self._translate()
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._show_progress)
        self._clock_timer.start()
        self._save()

    def _load_progress(self, case, save_path=None):
        self.case = case
        self.store = SessionStore(save_path if save_path is not None else ROOT / f"userdata/{case.id}.json")
        self._backup = None
        self._save_problem = None
        self._save_blocked = False
        try:
            self.session = self.store.load(self.case)
        except (OSError, ValueError, TypeError) as error:
            self.session = SessionState(self.case)
            try:
                self._backup = self.store.preserve_invalid()
            except OSError:
                self._save_blocked = True
                self._save_problem = str(error)

    def _build(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        self.title = QLabel()
        font = self.title.font()
        font.setPointSize(17)
        font.setBold(True)
        self.title.setFont(font)
        heading.addWidget(self.title, 1)
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("繁體中文", "zh-Hant")
        self.language.currentIndexChanged.connect(self._change_language)
        heading.addWidget(self.language)
        layout.addLayout(heading)
        self.subtitle, self.progress = QLabel(), QLabel()
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.progress)
        columns = QHBoxLayout()
        self.target_group, self.current_group = QGroupBox(), QGroupBox()
        left, right = QVBoxLayout(self.target_group), QVBoxLayout(self.current_group)
        self.target_info, self.score, self.clue, self.review = (QLabel() for _ in range(4))
        self.submission_feedback=SubmissionFeedback()
        for label in (self.target_info, self.score, self.submission_feedback, self.clue, self.review):
            label.setWordWrap(True)
            left.addWidget(label)
        self.score.setObjectName("case_score")
        score_font = self.score.font()
        score_font.setPointSize(16)
        score_font.setBold(True)
        self.score.setFont(score_font)
        self.clue.setObjectName("case_diagnosis")
        self.review.setObjectName("case_review")
        self.review_button = QPushButton()
        self.review_button.setObjectName("review_answer")
        self.review_button.clicked.connect(self._open_review)
        left.addWidget(self.review_button)
        left.addStretch()
        self.play_a = QPushButton()
        self.play_a.clicked.connect(lambda: self._prepare("a"))
        left.addWidget(self.play_a)
        self.editor = ParameterEditor(self.case)
        self.controls = self.editor.controls
        self.cutoff = self.controls.get("cutoff_hz")
        self.release = self.controls.get("release")
        self.cutoff_label = self.editor.labels.get("cutoff_hz")
        self.release_label = self.editor.labels.get("release")
        self.locked = QLabel()
        self.locked.setWordWrap(True)
        right.addWidget(self.editor)
        right.addWidget(self.locked)
        self.play_b = QPushButton()
        self.play_b.clicked.connect(lambda: self._prepare("b"))
        right.addWidget(self.play_b)
        self.history = QTableWidget(0, 4)
        self.history.setObjectName("submission_history")
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history.verticalHeader().hide()
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.setMinimumHeight(130)
        right.addWidget(self.history, 1)
        columns.addWidget(self.target_group, 1)
        columns.addWidget(self.current_group, 1)
        layout.addLayout(columns, 1)
        self.editor.changed.connect(self._parameters_changed)
        transport = QHBoxLayout()
        self.play_ab, self.compare_button, self.stop_button, self.restart_button = (QPushButton() for _ in range(4))
        for name, button in (("play_ab", self.play_ab), ("submit_answer", self.compare_button), ("stop", self.stop_button), ("restart_case", self.restart_button)):
            button.setObjectName(name)
            transport.addWidget(button, 1)
        self.play_ab.clicked.connect(lambda: self._prepare("ab"))
        self.compare_button.clicked.connect(lambda: self._prepare("compare"))
        self.stop_button.clicked.connect(self.stop)
        self.restart_button.clicked.connect(self._restart)
        layout.addLayout(transport)
        volume_row = QHBoxLayout()
        self.volume_label, self.volume_value = QLabel(), QLabel("35%")
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(35)
        self.volume.valueChanged.connect(self._volume_changed)
        volume_row.addWidget(self.volume_label)
        volume_row.addWidget(self.volume, 1)
        volume_row.addWidget(self.volume_value)
        layout.addLayout(volume_row)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedHeight(5)
        self.busy.hide()
        layout.addWidget(self.busy)
        self.status, self.device, self.note, self.save_warning = (QLabel() for _ in range(4))
        for label in (self.status, self.device, self.note, self.save_warning):
            label.setWordWrap(True)
            layout.addWidget(label)
        self.shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut.activated.connect(self.stop)

    def _translate(self):
        from .hover_help import apply_window_help
        text = TEXT[self._language]
        title = text["title"].replace("01", self.case.id[1:])
        self.setWindowTitle(title)
        self.title.setText(f"{title} · {self.case.title[self._language]}")
        self.subtitle.setText(self.case.description[self._language])
        self.target_group.setTitle(text["target"])
        self.current_group.setTitle(text["current"])
        for name in ("play_a", "play_b", "play_ab", "locked"):
            getattr(self, name).setText(text[name])
        if len(self.case.editable_parameters) == len(PARAMETERS):
            self.locked.setText("Notes and rhythm are fixed; all sound controls are available." if self._language == "en" else "音符與節奏固定；所有音色控制項均已開放。")
        self.note.setText(text["note"].format(hint=self.case.hint_threshold, passing=self.case.comparison.pass_score,
            component=self.case.comparison.component_floor, tail=self.case.comparison.tail_floor))
        self.editor.translate(self._language)
        self.review_button.setText("Review all controls" if self._language == "en" else "查看全部控制項復盤")
        self.volume_label.setText(text["volume"])
        for button, key in ((self.compare_button, "submit"), (self.stop_button, "stop"), (self.restart_button, "restart")):
            button.setText(text[key])
        self._status(self._status_key, **self._status_args)
        self._device()
        self._show_match()
        self._show_save_warning()
        apply_window_help(self, "tone", self._language)

    def _show_progress(self):
        text, session = TEXT[self._language], self.session
        phase = "solved" if session.solved else "practice" if session.practice else "playing"
        message = text["progress"].format(phase=text[phase], attempts=session.attempt_count, seconds=session.elapsed_seconds)
        if session.first_pass is not None:
            message += " · " + text["first"].format(total=session.first_pass.total, number=session.first_pass.number)
        self.progress.setText(message)

    def _status(self, key, **arguments):
        if key in ("compared", "ready", "idle"):
            self._status_key, self._status_args = key, arguments
            self.status.setText(TEXT[self._language][key])
        else:
            super()._status(key, **arguments)

    def _show_match(self):
        text, session = TEXT[self._language], self.session
        self._show_progress()
        record = session.last
        snapshot=lambda item:ScoreSnapshot(item.total,item.modules,item.version,item.number) if item else None
        previous=session.attempts[-2] if len(session.attempts)>1 else None
        self.submission_feedback.show_scores(snapshot(record),snapshot(previous),language=self._language,
            labels={key:value[self._language=='zh-Hant'] for key,value in GROUPS.items()},
            details=bool(record and record.total>=self.case.hint_threshold))
        self.target_info.setText(text["gate"].format(threshold=self.case.hint_threshold))
        if record and record.version != PROGRESS_VERSION:
            self.target_info.setText(self.target_info.text() + "\n" + text["legacy_note"])
        elif record and session.current_is_submitted and record.total >= self.case.hint_threshold and record.modules:
            self.target_info.setText(self.target_info.text() + "\n" + " · ".join(
                f"{GROUPS[key][self._language == 'zh-Hant']} {display_score(value)}" for key, value in record.modules.items()))
        if record is None:
            self.score.setText(text["unscored"])
        else:
            self.score.setText(text["score" if record.version == PROGRESS_VERSION else "legacy_score"].format(number=record.number, score=display_score(record.total),
                outcome=text["passed" if record.passed(self.case) else "retry"])
                + ("\n" + text["outdated"] if not session.current_is_submitted else ""))
        if self._submission_token is not None:
            self.clue.setText(text["comparing"])
        elif session.visible_diagnostics:
            codes = visible_clue_codes(session.visible_diagnostics, self.case)
            messages = [text.get(code, text["uncertain"]) if self.case.diagnostic_profile == "basic" and not code.startswith("progress_")
                        else describe_clue(code, self.case, self._language) for code in codes]
            self.clue.setText("\n\n".join(f"• {message}" for message in messages) if len(messages) > 1 else messages[0])
        else:
            self.clue.setText(text["changed"] if record and not session.current_is_submitted else "")
        if session.solved:
            if record.version == PROGRESS_VERSION:
                self.review.setText(("Case solved. Review the target controls and module progress." if self._language == "en" else "案件已解決，可查看目標控制項與各模組還原進度。"))
                if self.case.id == "T01":
                    label = "截止頻率" if self._language == "zh-Hant" else "Cutoff"
                    self.review.setText(self.review.text() + f"\n{label}: {self.case.reference.effects.filter.cutoff_hz:g} Hz; Release: {self.case.reference.patch.release:.2f} s.")
            elif self.case.id == "T01":
                self.review.setText(text["review"].format(cutoff=self.case.reference.effects.filter.cutoff_hz,
                    release=self.case.reference.patch.release, spectrum=record.spectrum, envelope=record.envelope, tail=record.tail))
            else:
                self.review.setText(("Case solved. Review the reference and your answer below." if self._language == "en" else "案件已解決，可查看參照與本次答案的控制項比較。"))
        else:
            self.review.clear()
        self.review.setVisible(session.solved)
        self.review_button.setVisible(session.solved)
        self.history.setHorizontalHeaderLabels(text["history"])
        self.history.setRowCount(len(session.attempts))
        for row, item in enumerate(session.attempts):
            score_label = display_score(item.total) + (" [audio v1]" if item.version != PROGRESS_VERSION else "")
            values = (str(item.number), score_label, text["yes" if item.total >= self.case.hint_threshold else "no"],
                      text["passed" if item.passed(self.case) else "retry"])
            for column, value in enumerate(values):
                self.history.setItem(row, column, QTableWidgetItem(value))
        if session.attempts:
            self.history.scrollToBottom()
        self._lock_controls()
        # Audio comparison temporarily disables controls. Resolve the rings
        # after restoring their enabled state, not during the pending lock.
        tone_guidance(self,visible_clue_codes(session.visible_diagnostics,self.case) if session.visible_diagnostics else ())

    def _lock_controls(self):
        pending = self._submission_token is not None
        self.editor.set_locked(pending or self.session.solved)
        self.compare_button.setEnabled(not pending and not self.session.solved)
        for control in (self.play_a, self.play_b, self.play_ab, self.restart_button):
            control.setEnabled(not pending)
        if hasattr(self, 'edit_bar'):
            self.edit_bar.refresh()

    def _sync_controls(self):
        self.editor.set_settings(self.session.current)

    def _parameters_changed(self, *_):
        if self._initializing or self._closed:
            return
        if self.session.solved:
            self._sync_controls()
            return
        self.stop()
        self.session.update(**self.editor.values())
        self.edit_bar.record(self.session.current)
        self._match_result = None
        self._show_match()
        self._status("updated")
        self._debounce.start()
        self._save()

    def _restore_edit(self, settings):
        self.stop()
        self.session.update(**self.case.parameters(settings))
        self._sync_controls()
        self._match_result = None
        self._show_match()
        self._status('updated')
        self._save()

    def _requests(self, mode):
        return {label: (settings, self.case.sequence) for label, settings in (("a", self.case.reference), ("b", self.session.current))
                if mode is None or mode in ("ab", "compare") or mode == label}

    def _preview_options(self):
        from ..audio.audio_output import audition_options
        return audition_options(self.case.id)

    def _comparison_options(self):
        result = {"comparison_config": self.case.comparison}
        if self.case.diagnostic_profile != "basic":
            result["diagnostic_context"] = DiagnosticContext(self.case.diagnostic_profile, self.case.sequence, self.case.editable_parameters)
        return result

    def _open_review(self):
        if not self.session.solved:
            return
        if self.property('studioEmbedded'):
            self.review_requested.emit()
            return
        zh = self._language == "zh-Hant"
        dialog = QDialog(self)
        dialog.setWindowTitle("案件復盤" if zh else "Case review")
        layout = QVBoxLayout(dialog)
        last = self.session.last
        if last.version == PROGRESS_VERSION:
            message = f"{last.total:.1f} / 100 · " + " · ".join(
                f"{GROUPS[key][zh]} {value:.1f}" for key, value in last.modules.items())
        else:
            message = f"{last.total:.1f} / 100 · Spectrum {last.spectrum:.1f} · Envelope {last.envelope:.1f} · Tail {last.tail:.1f} [audio v1]"
        summary = QLabel(message)
        summary.setWordWrap(True)
        layout.addWidget(summary)
        table = QTableWidget(len(self.case.editable_parameters), 3)
        table.setObjectName("review_controls")
        table.setHorizontalHeaderLabels(("控制項", "參照", "本次答案") if zh else ("Control", "Reference", "Your answer"))
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        reference = self.case.parameters(self.case.reference)
        def display(key, value):
            if PARAMETERS[key].kind == "bool":
                return ("開啟" if value else "關閉") if zh else ("On" if value else "Off")
            if key == "filter_mode":
                return ("低通" if value == "lowpass" else "高通") if zh else ("Low-pass" if value == "lowpass" else "High-pass")
            return str(value)
        for row, key in enumerate(self.case.editable_parameters):
            label = self.editor.labels[key].text()
            for column, value in enumerate((label, display(key, reference[key]), display(key, last.parameters[key]))):
                table.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("關閉" if zh else "Close")
        from .hover_help import set_help
        set_help(buttons.button(QDialogButtonBox.StandardButton.Close), "close_review", self._language)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(720, 520)
        dialog.exec()

    def _prepare(self, mode):
        if self._closed or self._submission_token is not None:
            return
        if mode == "compare":
            if self.session.solved:
                return
            try:
                self._submission_token = self.session.begin_submission()
            except (ValueError, RuntimeError) as error:
                self._status("error", message=str(error))
                return
            self._lock_controls()
        super()._prepare(mode)
        if mode == "compare" and self._match_revision is None:
            self.session.cancel_submission()
            self._submission_token = None
            self._show_match()

    def _matched(self, revision, result):
        if self._closed or revision != self._revision or revision != self._match_revision or self._submission_token is None:
            return
        was_solved = self.session.solved
        try:
            self.session.complete_submission(self._submission_token, result)
        except (ValueError, TypeError) as error:
            self._failed(revision, str(error))
            return
        self._submission_token = None
        super()._matched(revision, result)
        self._save()
        if not was_solved and self.session.solved:
            self.case_completed.emit()

    def _failed(self, revision, message):
        if self._closed or revision != self._revision:
            return
        self.session.cancel_submission()
        self._submission_token = None
        super()._failed(revision, message)
        self._show_match()

    def stop(self):
        super().stop()
        self.session.cancel_submission()
        self._submission_token = None
        self._show_match()

    def _restart(self):
        self.stop()
        self.session.restart()
        self.edit_bar.reset(self.session.current)
        self._match_result = None
        self._sync_controls()
        self._show_match()
        self._save()

    def _change_language(self):
        self._language = self.language.currentData()
        self.session.language = self._language
        self._translate()
        self._save()

    def _volume_changed(self, value):
        super()._volume_changed(value)
        self.session.volume = value / 100
        self._save()

    def _show_save_warning(self):
        text = TEXT[self._language]
        message = text["save_error"].format(message=self._save_problem) if self._save_problem else text["backup"] if self._backup else ""
        self.save_warning.setText(message)
        self.save_warning.setToolTip(str(self._backup or ""))
        self.save_warning.setVisible(bool(message))

    def _save(self):
        if self._initializing:
            return
        if not self._save_blocked:
            try:
                self.store.save(self.session)
                self._save_problem = None
            except (OSError, ValueError) as error:
                self._save_problem = str(error)
        self._show_save_warning()

    def closeEvent(self, event):
        if self._closed:
            event.accept()
            return
        self.stop()
        self._clock_timer.stop()
        self._save()
        super().closeEvent(event)


# Preserve the existing single-case entry and imports.
CaseOneWindow = CaseWindow
