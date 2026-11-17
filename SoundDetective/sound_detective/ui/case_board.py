"""Case selection is a draft until the player explicitly accepts a case."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QScrollArea

from ..game.storage import SessionStore
from ..game.hidden_sound import load_hidden_case, load_hidden_session
from ..game.melody import load_melody_cases, load_melody_session
from ..game.catalog import WORDLE_IDS, MELODY_IDS
from ..game.sound_categories import CATEGORIES, load_source_cases, load_source_session
from ..game.source_learning import selected_difficulty,source_path,with_difficulty,DIFFICULTIES
from .hover_help import set_help


class CaseBoard(QFrame):
    accepted = Signal(str)
    dismissed = Signal()

    def __init__(self, cases, progress_dir):
        super().__init__()
        self.setObjectName("panel")
        self.cases, self.progress_dir = cases, progress_dir
        self.wordle = load_hidden_case()
        self.melody_cases={case.id:case for case in load_melody_cases()}
        self.melody = self.melody_cases['W02']
        self.source_cases = load_source_cases()
        self.category = "all"
        self.language, self.mode, self.selected = "en", "tone", None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size: 27px; color: #f1dfb6;")
        layout.addWidget(self.heading)
        modes = QHBoxLayout()
        group = QButtonGroup(self)
        self.mode_buttons = {}
        for key in ("tone", "wordle"):
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

    def open(self, active_case, language):
        self.mode = "wordle" if active_case in WORDLE_IDS else "tone"
        self.selected = active_case if active_case in (*WORDLE_IDS, *(case.id for case in self.cases)) else None
        self.category = "all"
        self.translate(language)

    def set_category(self, category):
        if category not in CATEGORIES:
            return
        self.category = category
        self.refresh()

    def set_mode(self, mode):
        if mode not in self.mode_buttons:
            return
        if mode != self.mode:
            self.mode, self.selected = mode, None
        self.refresh()

    def translate(self, language):
        self.language = language
        zh = language == "zh-Hant"
        self.heading.setText("案件板" if zh else "Case Board")
        self.mode_buttons["tone"].setText("音色還原" if zh else "Timbre Cases")
        self.mode_buttons["wordle"].setText("聲音重建" if zh else "Sound Wordle")
        for key,button in self.category_buttons.items():
            button.setText(CATEGORIES[key][zh])
            set_help(button, "source_category", language)
        self.back_button.setText("返回房間" if zh else "Back to office")
        self.accept_button.setText("接受案件" if zh else "Accept case")
        for key, button in self.mode_buttons.items():
            set_help(button, f"mode_{key}", language)
        set_help(self.back_button, "back_room", language)
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
        available = self.cases if self.mode == "tone" else (self.wordle, self.melody, *self.source_cases,*tuple(self.melody_cases.values())[1:])
        if self.mode == "wordle" and self.category != "all":
            available = tuple(case for case in available if getattr(case,"category","classic") == self.category)
        if self.mode == "wordle":
            available = tuple(sorted(available, key=lambda case: case.id))
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
                    if case.id=='W01' or case.id in MELODY_IDS:
                        session = load_hidden_session(path) if case.id=='W01' else load_melody_session(path,case)
                    else:
                        difficulty=selected_difficulty(path)
                        session = load_source_session(source_path(path,difficulty),with_difficulty(case,difficulty))
                        status=DIFFICULTIES[difficulty][zh]
                    if session.solved:
                        status = "已揭曉 · 可練習" if zh else "Revealed · practice available"
                    status += f" · {session.attempts} " + ("次提交" if zh else "submissions")
                except (OSError, ValueError, TypeError, KeyError):
                    status = "進度待恢復" if zh else "Progress needs recovery"
            button.setText(f"{case.id}\n{case.title[self.language]}\n\n{status}")
            set_help(button, "case_card", self.language)
            button.clicked.connect(lambda checked=False, key=case.id: self.select(key))
            self.cards_layout.addWidget(button, index // 4, index % 4)
            self.cards[case.id] = button
        self.mode_buttons[self.mode].setChecked(True)
        self.accept_button.setEnabled(self.selected in self.cards and self.cards[self.selected].isEnabled())
        self.note.setText(("選擇案件並接受後，返回工作桌開始調查。" if zh else
                           "Accept a case, then return to the workbench to investigate.") if available else
                          ("目前沒有可用的音樂案件。" if zh else "No music cases available."))
        if self.mode == "wordle":
            self.note.setText("依口供合成聲音；W09 電線裡的幽靈位於噪聲與電子類，門鈴與節奏位於信號與旋律類。不限提交、免費提示，目標於通關後揭曉。" if zh else
                              "Build from witness clues. Find W09 Wire Ghost under Noise / electronics, or doorbell and rhythm cases under Signals / melody. Unlimited submissions; targets unlock after solving.")

    def select(self, case_id):
        selected_button = self.cards.get(case_id)
        if selected_button is None or not selected_button.isEnabled():
            self.accept_button.setEnabled(self.selected in self.cards and self.cards[self.selected].isEnabled())
            return
        self.selected = case_id
        for key, button in self.cards.items():
            button.setChecked(key == case_id)
        self.accept_button.setEnabled(selected_button.isEnabled())

    def _accept(self):
        if self.accept_button.isEnabled():
            self.accepted.emit(self.selected)
