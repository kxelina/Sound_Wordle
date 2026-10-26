"""Case selection is a draft until the player explicitly accepts a case."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QScrollArea

from ..game.storage import SessionStore
from ..game.hidden_sound import load_hidden_case, load_hidden_session
from ..game.melody import MelodyCase, load_melody_session
from ..game.sound_categories import CATEGORIES, load_source_cases, load_source_session
from ..game.source_learning import selected_difficulty,source_path,with_difficulty,DIFFICULTIES
from .hover_help import set_help


class CaseBoard(QFrame):
    accepted = Signal(str)
    free_requested = Signal()
    dismissed = Signal()

    def __init__(self, cases, music, progress_dir, *, music_status=None):
        super().__init__()
        self.setObjectName("panel")
        self.cases, self.music, self.progress_dir = cases, music, progress_dir
        self.music_status = music_status
        self.wordle = load_hidden_case()
        self.melody = MelodyCase()
        self.source_cases = load_source_cases()
        self.category = "all"
        self.language, self.mode, self.selected = "en", "tone", None
        self.music_room = False
        self.free_composition = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size: 27px; color: #f1dfb6;")
        layout.addWidget(self.heading)
        modes = QHBoxLayout()
        group = QButtonGroup(self)
        self.mode_buttons = {}
        for key in ("tone", "music", "wordle"):
            button = QPushButton()
            button.setObjectName(f"mode_{key}")
            button.setCheckable(True)
            group.addButton(button)
            button.clicked.connect(lambda checked=False, mode=key: self.set_mode(mode))
            modes.addWidget(button)
            self.mode_buttons[key] = button
        layout.addLayout(modes)
        self.category_row = QWidget()
        category_layout = QHBoxLayout(self.category_row)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(6)
        self.category_buttons = {}
        category_group = QButtonGroup(self)
        for key in CATEGORIES:
            button = QPushButton()
            button.setObjectName("wordle_category_"+key)
            button.setCheckable(True)
            button.setStyleSheet("font-size: 13px; padding: 6px 8px;")
            button.clicked.connect(lambda checked=False,value=key:self.set_category(value))
            category_group.addButton(button)
            category_layout.addWidget(button)
            self.category_buttons[key] = button
        layout.addWidget(self.category_row)
        card_body = QWidget()
        self.cards_layout = QGridLayout(card_body)
        for column in range(4):
            self.cards_layout.setColumnStretch(column, 1)
        card_scroll = QScrollArea()
        card_scroll.setWidgetResizable(True)
        card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        card_scroll.setWidget(card_body)
        layout.addWidget(card_scroll, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        row = QHBoxLayout()
        self.back_button, self.accept_button = QPushButton(), QPushButton()
        self.back_button.setObjectName("board_back")
        self.accept_button.setObjectName("accept_case")
        self.back_button.clicked.connect(self.dismissed)
        self.accept_button.clicked.connect(self._accept)
        row.addWidget(self.back_button)
        row.addStretch()
        row.addWidget(self.accept_button)
        layout.addLayout(row)

    def open(self, active_case, language, *, free_composition=False):
        self.free_composition = free_composition
        self.selected = "FREE" if free_composition else active_case
        self.music_room = bool(free_composition or active_case and active_case.startswith("M"))
        self.mode = "music" if self.music_room else "wordle" if active_case and active_case.startswith("W") else "tone"
        self.category = "all"
        self.translate(language)

    def set_category(self, category):
        if category not in CATEGORIES:
            return
        self.category = category
        self.refresh()

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode, self.selected = mode, None
        self.refresh()

    def translate(self, language):
        self.language = language
        zh = language == "zh-Hant"
        self.heading.setText("案件板" if zh else "Case Board")
        self.mode_buttons["tone"].setText("音色還原" if zh else "Timbre Cases")
        self.mode_buttons["music"].setText("音樂工作室" if zh else "Music Studio")
        self.mode_buttons["wordle"].setText("聲音重建" if zh else "Sound Wordle")
        for key,button in self.category_buttons.items():
            button.setText(CATEGORIES[key][zh])
            set_help(button, "source_category", language)
        self.back_button.setText(("返回錄音室" if zh else "Back to studio") if self.music_room else ("返回房間" if zh else "Back to office"))
        self.accept_button.setText("接受案件" if zh else "Accept case")
        for key, button in self.mode_buttons.items():
            set_help(button, f"mode_{key}", language)
        set_help(self.back_button, "back_composition_room" if self.free_composition else "back_music_room" if self.music_room else "back_room", language)
        set_help(self.accept_button, "accept", language)
        self.refresh()

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.cards = {}
        zh = self.language == "zh-Hant"
        self.category_row.setVisible(self.mode == "wordle")
        for key,button in self.category_buttons.items():
            button.setChecked(key == self.category)
        available = self.cases if self.mode == "tone" else (self.wordle, self.melody, *self.source_cases) if self.mode == "wordle" else ((self.music,) if self.music else ())
        if self.mode == "wordle" and self.category != "all":
            available = tuple(case for case in available if getattr(case,"category","classic") == self.category)
        for index, case in enumerate(available):
            button = QPushButton()
            button.setObjectName(f"case_card_{case.id}")
            button.setCheckable(True)
            button.setChecked(case.id == self.selected)
            button.setMinimumHeight(105 if self.mode == "wordle" else 140)
            status = "尚未完成" if zh else "Unsolved"
            if self.mode == "tone":
                try:
                    session = SessionStore(self.progress_dir / f"{case.id}.json").load(case)
                    if session.first_pass:
                        status = "已完成" if zh else "Cleared"
                    if session.last:
                        status += f" · {session.last.total:.1f} / 100"
                except (OSError, ValueError, TypeError):
                    status = "進度待恢復" if zh else "Progress needs recovery"
            elif self.mode == "wordle":
                try:
                    path = self.progress_dir / "wordle" / f"{case.id}.json"
                    if case.id in ("W01","W02"):
                        loader = load_hidden_session if case.id == "W01" else load_melody_session
                        session = loader(path)
                    else:
                        difficulty=selected_difficulty(path)
                        session = load_source_session(source_path(path,difficulty),with_difficulty(case,difficulty))
                        status=DIFFICULTIES[difficulty][zh]
                    if session.solved:
                        status = "已揭曉 · 可練習" if zh else "Revealed · practice available"
                    status += f" · {session.attempts} " + ("次提交" if zh else "submissions")
                except (OSError, ValueError, TypeError, KeyError):
                    status = "進度待恢復" if zh else "Progress needs recovery"
            else:
                # Opening the board never discloses accepted song answers.
                path = self.progress_dir / "music" / f"{case.id}.json"
                try:
                    import json
                    from ..game.music_cases import MusicSession
                    data = json.loads(path.read_text("utf-8")) if path.exists() else None
                    if data and MusicSession.from_dict(data["session"], case).first_clear:
                        status = "已完成" if zh else "Cleared"
                except (OSError, ValueError, TypeError, KeyError):
                    pass
                if not case.source.is_file() or not case.evidence.is_file() or self.music_status is not None and not self.music_status.available:
                    status = "本機音源暫不可用" if zh else "Local audio unavailable"
                    button.setEnabled(False)
            button.setText(f"{case.id}\n{case.title[self.language]}\n\n{status}")
            set_help(button, "case_card", self.language)
            button.clicked.connect(lambda checked=False, key=case.id: self.select(key))
            self.cards_layout.addWidget(button, index // 4, index % 4)
            self.cards[case.id] = button
        if self.mode == "music":
            button = QPushButton("自由創作\n\n編寫旋律、調整音色與效果\n不評分 · 獨立草稿" if zh else
                                 "Free composition\n\nWrite melodies, shape timbre and effects\nNo grading · separate draft")
            button.setObjectName("free_composition_card")
            button.setCheckable(True)
            button.setChecked(self.selected == "FREE")
            button.setMinimumHeight(140)
            set_help(button, "free_card", self.language)
            button.clicked.connect(lambda: self.select("FREE"))
            index = len(available)
            self.cards_layout.addWidget(button, index // 4, index % 4)
            self.cards["FREE"] = button
        self.mode_buttons[self.mode].setChecked(True)
        self.accept_button.setEnabled(self.selected in self.cards and self.cards[self.selected].isEnabled())
        self.note.setText(("選擇案件並接受後，返回工作桌開始調查。" if zh else
                           "Accept a case, then return to the workbench to investigate.") if available else
                          ("目前沒有可用的音樂案件。" if zh else "No music cases available."))
        if self.mode == "wordle":
            self.note.setText("選擇自然、樂器或噪聲案件，依口供合成聲音。W01/W02 位於信號與旋律類。不限提交、免費提示；目標於通關後揭曉。" if zh else
                              "Choose Nature, Instruments or Noise and build from witness clues. W01/W02 remain under Signals & melody. Unlimited submissions, free clues; targets unlock after solving.")
        elif self.mode == "music":
            self.note.setText("選擇音樂修復案件或自由創作，接受後進入音樂工作室；創作不評分，草稿獨立儲存。" if zh else
                              "Choose a restoration case or free composition, then accept to enter the music studio. Free drafts are saved separately, without grading.")
            if self.music_status is not None and not self.music_status.available:
                self.note.setText("M01 需要另外提供本機歌曲素材；目前可以選擇自由創作，或切換至音色案件與聲音重建。" if zh else
                                  "M01 needs separately supplied local music assets. Free composition, Timbre Cases and Sound Wordle remain available.")

    def select(self, case_id):
        self.selected = case_id
        for key, button in self.cards.items():
            button.setChecked(key == case_id)
        self.accept_button.setEnabled(True)

    def _accept(self):
        if self.accept_button.isEnabled():
            if self.selected == "FREE":
                self.free_requested.emit()
            else:
                self.accepted.emit(self.selected)
