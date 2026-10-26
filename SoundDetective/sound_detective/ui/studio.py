"""Perspective desktop shell: menu, preferences and interactive office."""

from pathlib import Path
import time

from PySide6.QtCore import QEvent, QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsBlurEffect, QGraphicsItem, QGraphicsPathItem,
    QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSlider, QVBoxLayout, QWidget, QApplication,
)

from ..audio.sc_client import ROOT
from ..game.desktop import DesktopStore, window_sizes
from ..game.cases import load_campaign
from ..game.music_cases import load_music_case
from ..game.availability import music_availability
from ..game.player_journey import JourneyStore
from ..game.evidence import EvidenceStore
from ..game.catalog import MELODY_IDS
from .case_board import CaseBoard
from .hardware import InlineChoices
from .hover_help import set_help, show_scene_help
from .studio_scenes import SCENES
from ..audio.ui_sounds import play_widget_click, ui_sounds, remaining_click_ms


ART = ROOT / "assets/ui"
TEXT = {
    "en": {
        "start": "Start Game", "settings": "Settings", "exit": "Exit", "back": "Back",
        "menu": "Main menu", "size": "Window size", "volume": "Master volume", "language": "Language",
        "desk": "Workbench", "board": "Case Board", "office": "Detective's office",
        "room_help": "Choose a case on the wall board. Click the desk to work with the equipment.",
        "backup": "Unreadable settings were backed up. Default settings are in use.",
        "save_error": "Settings could not be saved. Your original file has been retained.",
        "tagline": "Every sound leaves a trace.",
        "desk_help": "Click a device to examine or adjust the current case.",
        "tape": "Evidence player", "synth": "Synthesizer · Harmonics / ADSR / Filter",
        "analyzer": "Analysis screen", "delay": "Delay processor", "reverb": "Reverb processor",
        "choose_case": "Select a case on the wall board before using the equipment.",
        "back_room": "Back to office",
        "back_desk": "Back to desk", "case_error": "This case could not be loaded. Check its saved progress and audio assets.",
        "music_synth": "Filter / Pitch workstation",
        "music_delay": "Echo canceller", "music_reverb": "Room recovery", "music_analyzer": "Repair calibration log",
        "music_office": "Music restoration studio", "music_board": "Session board", "music_desk": "Restoration console",
        "music_room_help": "Choose a case on the wall board, then click the console to restore the recording.",
        "music_desk_help": "Tape: listen · Console: filter / pitch · Upper rack: echo · Lower rack: reverb · Screen: log",
        "music_back_room": "Back to studio",
        "composition_office": "Music studio", "composition_title": "Free composition",
        "composition_desk": "Composition console", "composition_board": "Studio board",
        "composition_room_help": "Click the console to compose, or open the wall board to choose another activity.",
        "composition_desk_help": "Console: piano roll / synthesizer · Rack: Delay / Reverb · Tape: listen to your composition",
        "wordle_synth": "Sound workshop · ADSR / Harmonics",
        "melody_synth": "Melody workshop · Piano roll / Synthesizer",
        "source_synth": "Sound-source workshop · Noise / Pitch / Envelope",
        "tutorial": "Learn to play", "review_page": "Case review",
        "review_back": "Back to case",
        "journey_backup": "Tutorial/review records were backed up after a read error. Case progress is retained.",
        "journey_save_error": "Tutorial/review records could not be saved. Case progress is stored separately.",
    },
    "zh-Hant": {
        "start": "開始遊戲", "settings": "設定", "exit": "退出", "back": "返回",
        "menu": "主選單", "size": "視窗大小", "volume": "主音量", "language": "語言",
        "desk": "工作桌", "board": "案件板", "office": "偵探工作室",
        "room_help": "在牆上案件板選擇案件，點擊工作桌使用設備。",
        "backup": "無法讀取的設定已備份，目前使用預設值。",
        "save_error": "無法儲存設定，原檔已保留。",
        "tagline": "每個聲音，都留下了線索。",
        "desk_help": "點擊設備，檢視或調整目前案件的聲音。",
        "tape": "證物播放器", "synth": "合成器 · 諧波 / ADSR / 濾波",
        "analyzer": "分析屏幕", "delay": "回聲處理器", "reverb": "混響處理器",
        "choose_case": "請先在牆上案件板選擇案件，再使用設備。", "back_room": "返回房間",
        "back_desk": "返回桌面", "case_error": "無法載入此案件，請檢查進度及音源檔案。",
        "music_synth": "頻段修復／音高校準",
        "music_delay": "回聲抵消器", "music_reverb": "空間修復器", "music_analyzer": "修復校準記錄",
        "music_office": "音樂修復工作室", "music_board": "修復案件板", "music_desk": "修復工作台",
        "music_room_help": "在牆上案件板選擇修復案件，再點調音台進入設備近景。",
        "music_desk_help": "磁帶機：試聽｜調音台：濾波／校音｜機架：回聲／混響｜屏幕：記錄",
        "music_back_room": "返回錄音室",
        "composition_office": "音樂工作室", "composition_title": "自由創作",
        "composition_desk": "創作工作台", "composition_board": "錄音室案件板",
        "composition_room_help": "點調音台進入自由創作，或在牆上案件板選擇其他玩法。",
        "composition_desk_help": "調音台：卷簾／合成器｜機架：Delay／Reverb｜磁帶機：試聽創作",
        "wordle_synth": "聲音工作台 · ADSR / 諧波",
        "melody_synth": "旋律工作台 · 鋼琴卷簾 / 合成器",
        "source_synth": "聲源工作台 · 噪聲 / 音高 / 包絡",
        "tutorial": "新手練習", "review_page": "結案復盤",
        "review_back": "返回案件",
        "journey_backup": "教程／復盤記錄讀取失敗，已先備份；案件進度仍保留。",
        "journey_save_error": "無法儲存教程／復盤記錄；案件進度另行保存。",
    },
}

STYLE = """
QWidget { color: #eee5d2; font-family: 'Segoe UI', 'Microsoft JhengHei UI'; font-size: 15px; }
QDialog { background: #1e231f; }
QFrame#panel { background: rgba(25, 24, 22, 242); border: 1px solid #73664d; border-radius: 8px; }
QPushButton { background: rgba(28, 29, 27, 225); border: 1px solid #8b7959; border-radius: 4px; padding: 11px 22px; }
QPushButton:hover, QPushButton:focus { background: #494235; border: 1px solid #e4c78a; }
QPushButton:pressed { background: #65563a; }
QPushButton:checked { background: #514936; border: 1px solid #e4c78a; }
QPushButton:disabled { color: #827e72; border-color: #4f4b40; }
QLabel { background: transparent; }
QComboBox { background: #292b28; border: 1px solid #847353; border-radius: 3px; padding: 8px 12px; min-height: 22px; }
QComboBox QAbstractItemView { background: #292b28; color: #eee5d2; selection-background-color: #65563a; }
QSlider::groove:horizontal { background: #4b493e; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #bea36c; border-radius: 2px; }
QSlider::handle:horizontal { background: #f0dfb7; width: 16px; margin: -6px 0; border-radius: 7px; }
QSlider::groove:vertical { background: #4b493e; width: 5px; border-radius: 2px; }
QSlider::add-page:vertical { background: #bea36c; border-radius: 2px; }
QSlider::handle:vertical { background: #f0dfb7; height: 14px; margin: 0 -5px; border-radius: 6px; }
QGroupBox { border: 1px solid #75674e; border-radius: 4px; margin-top: 13px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #e4ca93; }
QAbstractSpinBox, QLineEdit { background: #292e2b; color: #eee5d2; border: 1px solid #75674e; padding: 5px; }
QTableWidget { background: #202623; color: #eee5d2; gridline-color: #4f594f; border: 0; }
QHeaderView::section { background: #373c34; color: #eee5d2; border: 0; padding: 5px; }
QTabWidget::pane { border: 1px solid #75674e; background: #222823; }
QTabBar::tab { background: #30362f; color: #c8c1ac; padding: 7px 12px; }
QTabBar::tab:selected { background: #63563e; color: #f4e4bd; }
QScrollArea, QScrollArea QWidget { background: transparent; }
"""


def polygon(points):
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(*point)
    path.closeSubpath()
    return path


class Hotspot(QGraphicsPathItem):
    """The painted contour is also the hit region, in scene coordinates."""

    def __init__(self, key, path, activate, hover, *, persistent=True):
        super().__init__(path)
        self.key, self.activate, self.hover = key, activate, hover
        self.highlighted = False
        self.persistent = persistent
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(3)
        self.setPen(QPen(QColor("#d9bd7f"), 1.4))

    def paint(self, painter, option, widget=None):
        strong = self.highlighted or self.hasFocus()
        if not strong and not self.persistent:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(224, 192, 124, 100 if strong else 65), 7 if strong else 5))
        painter.drawPath(self.path())
        painter.setPen(QPen(QColor(247, 215, 153, 255 if strong else 220), 2.2 if strong else 1.6))
        painter.drawPath(self.path())

    def hoverEnterEvent(self, event):
        self.highlighted = True
        self.hover(self.key)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.highlighted = False
        self.hover(None)
        self.update()
        super().hoverLeaveEvent(event)

    def focusInEvent(self, event):
        self.hover(self.key)
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.hover(None)
        self.update()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activate(self.key)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activate(self.key)
            event.accept()
        else:
            super().keyPressEvent(event)


class OfficeView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(0, 0, 1280, 720, self))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#10110f"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.ToolTip and show_scene_help(self, event):
            return True
        return super().viewportEvent(event)


class StudioWindow(QMainWindow):
    page_changed = Signal(str)
    hotspot_activated = Signal(str)
    volume_changed = Signal(float)

    def __init__(self, *, progress_dir=None, animation_ms=520, tone_factory=None, music_factory=None, wordle_factory=None, melody_factory=None):
        super().__init__()
        self.progress_dir = Path(progress_dir or ROOT / "userdata")
        self.store = DesktopStore(self.progress_dir / "desktop-preferences.json")
        self.preferences = self.store.load()
        self.journey = JourneyStore(self.progress_dir/'player-journey.json')
        self.source_journeys={}
        self.evidence_store=EvidenceStore(self.progress_dir/'evidence-cabinet.json')
        for record in self.journey.reviews.values():
            if record.kind!='music' and record.clips['final'] is not None:self.evidence_store.remember(record)
        self.cabinet_panel=self.cabinet_proxy=None
        self._cabinet_return='room'
        self._has_prior_play = any(self.progress_dir.glob('T*.json')) or any((self.progress_dir/'wordle').glob('W*.json')) or any((self.progress_dir/'music').glob('M*.json'))
        self.tutorial_panel = self.tutorial_proxy = None
        self.debrief_panel = self.debrief_proxy = None
        self._tutorial_return = 'menu'
        self._review_return = 'device'
        self._device_started = None
        self._play_clock = time.monotonic
        self.setProperty("uiAudioVolume", self.preferences.volume / 100)
        self.page, self._settings_return = "menu", "menu"
        self._hovered = None
        self._closed = False
        self._exit_timer = QTimer(self)
        self._exit_timer.setSingleShot(True)
        self._exit_timer.timeout.connect(self._exit_after_click)
        self.animation_ms = animation_ms
        self.controller = self.device_proxy = None
        self.current_device = "synth"
        self._tone_factory, self._music_factory = tone_factory, music_factory
        self._wordle_factory = wordle_factory
        self._melody_factory = melody_factory
        self.cases = load_campaign()
        try:
            self.music = load_music_case(verify=False)
        except (OSError, ValueError, TypeError, KeyError):
            self.music = None
        self.music_status = music_availability()
        self.view = OfficeView(self)
        self.setCentralWidget(self.view)
        scene = self.view.scene()
        self.scene_key = "office"
        self._art_cache = {}
        room, desk = self._scene_pixmaps(self.scene_key)
        self.background = scene.addPixmap(room)
        self.blur = QGraphicsBlurEffect()
        self.blur.setBlurHints(QGraphicsBlurEffect.BlurHint.AnimationHint)
        self.background.setGraphicsEffect(self.blur)
        self.desk_background = scene.addPixmap(desk)
        self.desk_blur = QGraphicsBlurEffect()
        self.desk_background.setGraphicsEffect(self.desk_blur)
        self.shade = scene.addRect(QRectF(0, 0, 1280, 720), QPen(Qt.PenStyle.NoPen), QColor(0, 0, 0, 115))
        self.shade.setZValue(1)
        self.hotspots = {}
        for key, points in SCENES[self.scene_key].room_hotspots.items():
            item = Hotspot(key, polygon(points), self._activate_hotspot, self._hover)
            scene.addItem(item)
            self.hotspots[key] = item
        self._build_menu()
        self._build_settings()
        self._build_room_chrome()
        self.board = CaseBoard(self.cases, self.music, self.progress_dir, music_status=self.music_status)
        self.board.accepted.connect(self._accept_case)
        self.board.free_requested.connect(self.open_free_composition)
        self.board.dismissed.connect(lambda: self._show_page("room"))
        self.board_proxy = self._proxy(self.board, 100, 86, 1080, 550)
        self.device_hotspots = {}
        for key, points in SCENES[self.scene_key].devices.items():
            item = Hotspot(key, polygon(points), self._activate_device, self._hover, persistent=False)
            scene.addItem(item)
            self.device_hotspots[key] = item
        self.transition = QVariantAnimation(self)
        self.transition.setDuration(animation_ms)
        self.transition.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.transition.setStartValue(0.)
        self.transition.setEndValue(1.)
        self.transition.valueChanged.connect(self._animate_room)
        self.transition.finished.connect(self._finish_start)
        self.desk_transition = QVariantAnimation(self)
        self.desk_transition.setDuration(min(animation_ms, 350))
        self.desk_transition.setStartValue(0.)
        self.desk_transition.setEndValue(1.)
        self.desk_transition.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.desk_transition.valueChanged.connect(lambda value: self.desk_background.setOpacity(value))
        self.desk_transition.finished.connect(lambda: self._show_page("desk"))
        self._translate()
        sizes = self._sizes()
        requested = (self.preferences.width, self.preferences.height)
        size = requested if requested in sizes else sizes[-1]
        self.resize(*size)
        self.setMinimumSize(320, 180)
        self.setWindowTitle("Sound Detective")
        self._show_page("menu")

    @property
    def language(self):
        return self.preferences.language

    @property
    def free_composition(self):
        if self.preferences.active_case != "W02":
            return False
        if self.controller is not None and self.controller.case.id == "W02":
            return self.controller.session.mode == "free"
        # Startup has no controller. Inspect the saved mode without rewriting it.
        from ..game.melody import load_melody_session
        try:
            return load_melody_session(self.progress_dir/"wordle/W02.json").mode == "free"
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def _scene_pixmaps(self, key):
        if key not in self._art_cache:
            definition = SCENES[key]
            images = []
            for filename in (definition.room_art, definition.desk_art):
                pixmap = QPixmap(str(ART / filename))
                if pixmap.isNull():
                    raise FileNotFoundError(f"Studio artwork is missing: {filename}")
                images.append(pixmap.scaled(1280, 720, Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
            self._art_cache[key] = tuple(images)
        return self._art_cache[key]

    def _set_environment(self, key):
        if key == self.scene_key:
            return
        room, desk = self._scene_pixmaps(key)
        self.background.setPixmap(room)
        self.desk_background.setPixmap(desk)
        self.scene_key = key
        definition = SCENES[key]
        for name, item in self.hotspots.items():
            item.setPath(polygon(definition.room_hotspots[name]))
        for name, item in self.device_hotspots.items():
            item.setPath(polygon(definition.devices[name]))

    def _room_back_key(self):
        return ('back' if self.page in ('tutorial','cabinet') else 'review_back' if self.page=='review' else "menu" if self.page=="room" else "back_desk" if self.page=="device" else
                "music_back_room" if self.scene_key == "music" else "back_room")

    def _update_room_title(self):
        text = TEXT[self.language]
        if self.page=='cabinet':
            self.room_title.setText('SOUND DETECTIVE  /  '+('聲音證物收藏櫃' if self.language=='zh-Hant' else 'Evidence cabinet'))
            return
        if self.page in ('tutorial','review'):
            self.room_title.setText('SOUND DETECTIVE  /  '+text['tutorial' if self.page=='tutorial' else 'review_page'])
            return
        heading = "SOUND DETECTIVE  /  "
        if self.scene_key == "music":
            heading += text["composition_office" if self.free_composition else "music_office"] + "  /  "
        heading += text["composition_title"] if self.free_composition else self.preferences.active_case or text["office"]
        if self.page == "device":
            heading += "  /  " + self._device_label(self.current_device)
        self.room_title.setText(heading)

    def _proxy(self, widget, x, y, width, height):
        widget.setProperty("uiAudioVolume", self.preferences.volume / 100)
        if not isinstance(widget, QFrame):
            widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        local_style = widget.styleSheet()
        widget.setStyleSheet(STYLE + (f"\n{type(widget).__name__} {{ {local_style} }}" if local_style else ""))
        widget.setFixedSize(width, height)
        proxy = self.view.scene().addWidget(widget)
        proxy.setPos(x, y)
        proxy.setZValue(10)
        return proxy

    def _button(self, key, slot):
        button = QPushButton()
        button.setObjectName(key)
        button.clicked.connect(slot)
        return button

    def _build_menu(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        title = QWidget()
        title_layout = QVBoxLayout(title)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        self.menu_title_top = QLabel("SOUND")
        self.menu_title_main = QLabel("DETECTIVE")
        self.menu_title_top.setStyleSheet("font-family: Georgia; font-size: 35px; font-style: italic; letter-spacing: 12px; color: #cbb889;")
        self.menu_title_main.setStyleSheet("font-family: Georgia; font-size: 66px; letter-spacing: 5px; color: #f3e5c7;")
        for label in (self.menu_title_top, self.menu_title_main):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_layout.addWidget(label)
        layout.addWidget(title)
        self.tagline = QLabel()
        self.tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline.setStyleSheet("font-family: Georgia, 'Microsoft JhengHei UI'; font-style: italic; font-size: 16px; letter-spacing: 1px; color: #bbad90;")
        layout.addWidget(self.tagline)
        layout.addSpacing(38)
        self.start_button = self._button("start", self.start_game)
        self.settings_button = self._button("settings", self.open_settings)
        self.exit_button = self._button("exit", self._exit_after_click)
        self.tutorial_button = self._button('open_tutorial', self.open_tutorial)
        for button in (self.start_button, self.tutorial_button, self.settings_button, self.exit_button):
            button.setMinimumHeight(52)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)
        self.tutorial_button.setMinimumHeight(42)
        layout.addStretch()
        self.menu_proxy = self._proxy(widget, 360, 120, 560, 500)

    def _build_settings(self):
        widget = QFrame()
        widget.setObjectName("panel")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(10)
        self.settings_title = QLabel()
        self.settings_title.setStyleSheet("font-size: 27px; color: #f1dfb6;")
        layout.addWidget(self.settings_title)
        self.setting_labels = {}
        for key in ("size", "volume", "language"):
            label = QLabel()
            self.setting_labels[key] = label
            layout.addWidget(label)
            if key == "size":
                self.size_combo = InlineChoices(columns=3)
                self.size_combo.setObjectName("window_size")
                self.size_combo.activated.connect(self._size_changed)
                layout.addWidget(self.size_combo)
            elif key == "volume":
                row = QHBoxLayout()
                self.volume_slider = QSlider(Qt.Orientation.Horizontal)
                self.volume_slider.setObjectName("master_volume")
                self.volume_slider.setRange(0, 100)
                self.volume_slider.setValue(self.preferences.volume)
                self.volume_label = QLabel(f"{self.preferences.volume}%")
                self.volume_label.setMinimumWidth(48)
                self.volume_slider.valueChanged.connect(self._volume_changed)
                row.addWidget(self.volume_slider, 1)
                row.addWidget(self.volume_label)
                layout.addLayout(row)
            else:
                self.language_combo = InlineChoices()
                self.language_combo.setObjectName("desktop_language")
                self.language_combo.addItem("English", "en")
                self.language_combo.addItem("繁體中文", "zh-Hant")
                self.language_combo.setCurrentIndex(0 if self.language == "en" else 1)
                self.language_combo.currentIndexChanged.connect(self._language_changed)
                layout.addWidget(self.language_combo)
        self.settings_back = self._button("settings_back", self.close_settings)
        self.diagnostics_button = QPushButton()
        self.diagnostics_button.clicked.connect(self.open_diagnostics)
        layout.addStretch()
        layout.addWidget(self.diagnostics_button)
        layout.addWidget(self.settings_back)
        self.settings_proxy = self._proxy(widget, 330, 60, 620, 600)

    def _build_room_chrome(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.room_title = QLabel()
        self.room_title.setStyleSheet("font-size: 19px; color: #fff0d4; background: rgba(15,18,16,190); padding: 12px;")
        self.room_settings = self._button("room_settings", self.open_settings)
        self.room_review = self._button('open_debrief', self.open_review)
        self.room_cabinet=self._button('evidence_cabinet',self.open_cabinet)
        self.room_menu = self._button("room_menu", self.go_back)
        layout.addWidget(self.room_title, 1)
        self.room_title.setMinimumWidth(0)
        layout.addWidget(self.room_review)
        layout.addWidget(self.room_cabinet)
        layout.addWidget(self.room_settings)
        layout.addWidget(self.room_menu)
        self.room_proxy = self._proxy(widget, 30, 22, 1220, 52)
        self.caption = QLabel()
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setStyleSheet("color: #eee3c9; background: rgba(15,18,16,210); padding: 10px; border-radius: 4px;")
        self.caption_proxy = self._proxy(self.caption, 245, 660, 790, 40)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        self.warning.setStyleSheet("color: #f4dba4; background: rgba(25,24,22,240); padding: 6px;")
        self.warning_proxy = self._proxy(self.warning, 50, 620, 1180, 35)

    def _translate(self):
        text = TEXT[self.language]
        self.start_button.setText(text["start"])
        self.room_cabinet.setText('收藏櫃' if self.language=='zh-Hant' else 'Cabinet')
        self.settings_button.setText(text["settings"])
        self.exit_button.setText(text["exit"])
        menu_font = "'Courier New'" if self.language == "en" else "'KaiTi', 'STKaiti', 'Microsoft JhengHei UI'"
        for button in (self.start_button, self.tutorial_button, self.settings_button, self.exit_button):
            button.setStyleSheet(f"""
                QPushButton {{ font-family: {menu_font}; font-size: 25px;
                    letter-spacing: 3px; color: #d5c8ab; background: transparent;
                    border: none; border-radius: 0; padding: 8px 18px; }}
                QPushButton:hover, QPushButton:focus {{ color: #ffe2a3;
                    background: transparent; border: none; }}
                QPushButton:pressed {{ color: #bfa16c; background: transparent; border: none; }}
            """)
        self.tagline.setText(text["tagline"])
        self.settings_title.setText(text["settings"])
        self.settings_back.setText(text["back"])
        self.tutorial_button.setText(text['tutorial'])
        self.room_review.setText(text['review_page'])
        self.diagnostics_button.setText('啟動診斷' if self.language == 'zh-Hant' else 'Startup diagnostics')
        set_help(self.diagnostics_button, 'diagnostics', self.language)
        self._update_room_title()
        self.room_settings.setText(text["settings"])
        self.room_menu.setText(text[self._room_back_key()])
        for key, label in self.setting_labels.items():
            label.setText(text[key])
        if hasattr(self, "device_hotspots"):
            self.board.translate(self.language)
        self._hover(self._hovered)
        self.warning.setText(text.get(self.store.warning, ""))
        self.warning_proxy.setVisible(bool(self.store.warning))
        if self.journey.warning and not self.store.warning:
            self.warning.setText(text.get('journey_'+self.journey.warning,''))
            self.warning_proxy.setVisible(True)
        if self.controller is not None:
            self.controller.language.setCurrentIndex(0 if self.language == "en" else 1)
            self.controller.present_device(self.current_device)
        self._apply_hover_help()
        if self.tutorial_panel is not None:self.tutorial_panel.translate(self.language)
        if self.debrief_panel is not None:self.debrief_panel.translate(self.language)
        if self.cabinet_panel is not None:self.cabinet_panel.translate(self.language)

    def _apply_hover_help(self):
        language = self.language
        for widget, key in ((self.start_button, "start"), (self.settings_button, "settings"),
                            (self.exit_button, "exit"), (self.room_settings, "settings"),
                            (self.settings_back, "back_settings"), (self.volume_slider, "volume")):
            set_help(widget, key, language)
        set_help(self.tutorial_button,'open_tutorial',language)
        set_help(self.room_review,'open_debrief',language)
        set_help(self.room_cabinet,'evidence_cabinet',language)
        back = "back_desk" if self.page == "device" else "back_menu" if self.page == "room" else "back_room"
        if self.page=='tutorial':back='tutorial_skip'
        elif self.page=='review':back='debrief_back'
        if back == "back_room" and self.scene_key == "music":
            back = "back_composition_room" if self.free_composition else "back_music_room"
        set_help(self.room_menu, back, language)
        for control, key in ((self.size_combo, "size"), (self.language_combo, "language")):
            set_help(control, key, language)
            for button in control.buttons:
                set_help(button, key, language)
        for key, item in self.hotspots.items():
            prefix = "composition" if self.free_composition else "music"
            set_help(item, f"{prefix}_{key}" if self.scene_key == "music" else key, language)
        for key, item in self.device_hotspots.items():
            role = "device_melody" if key == "synth" and self.preferences.active_case in MELODY_IDS else (
                "device_music" if key == "synth" and (self.preferences.active_case or "").startswith("M") else f"device_{key}")
            if self.preferences.active_case in ("W03","W04","W05","W06"):
                if key == "synth":
                    role = "source_workshop"
                elif key == "analyzer":
                    role = "source_analysis"
            if key == "analyzer" and (self.preferences.active_case or "").startswith("M"):
                role = "device_music_notes"
            elif key in ("delay", "reverb") and (self.preferences.active_case or "").startswith("M"):
                role = f"device_music_{key}"
            set_help(item, role, language)

    def _show_page(self, page):
        self._flush_device_time()
        if self.page=='tutorial' and page!='tutorial' and self.tutorial_panel is not None:self.tutorial_panel.stop()
        if self.page=='review' and page!='review' and self.debrief_panel is not None:self.debrief_panel.stop()
        if self.page=='cabinet' and page!='cabinet' and self.cabinet_panel is not None:self.cabinet_panel.stop()
        if self.page == "device" and page != "device" and self.controller:
            if not (self.preferences.active_case.startswith("M") and self.controller.session.solved and page in ("desk", "room", "settings")):
                self.controller.stop()
            self.controller._save()
        self.page = page
        base = self._settings_return if page == "settings" else page
        music = (self.preferences.active_case or "").startswith("M") or self.free_composition
        self._set_environment("music" if music and base != "menu" else "office")
        self.menu_proxy.setVisible(page == "menu")
        self.settings_proxy.setVisible(page == "settings")
        self.room_proxy.setVisible(page in ("room", "desk", "device","tutorial","review","cabinet"))
        self.caption_proxy.setVisible(page in ("room", "desk"))
        self.board_proxy.setVisible(page == "board")
        self.desk_background.setVisible(base in ("desk", "device", "desk_transition","tutorial","review","cabinet"))
        self.desk_background.setOpacity(0 if page == "desk_transition" else 1)
        self.desk_blur.setBlurRadius(0 if page in ("desk", "desk_transition") else 16)
        self.room_menu.setText(TEXT[self.language][self._room_back_key()])
        if self.device_proxy is not None:
            self.device_proxy.setVisible(page == "device")
        if self.tutorial_proxy is not None:self.tutorial_proxy.setVisible(page=='tutorial')
        if self.debrief_proxy is not None:self.debrief_proxy.setVisible(page=='review')
        if self.cabinet_proxy is not None:self.cabinet_proxy.setVisible(page=='cabinet')
        self.room_review.setVisible(page not in ('tutorial','review','cabinet'))
        self.room_cabinet.setVisible(page not in ('tutorial','review','cabinet'))
        self.room_review.setEnabled(self._review_available())
        if self.controller and page == "menu":
            self.controller.stop()
        self._update_room_title()
        for item in self.hotspots.values():
            item.setVisible(page == "room")
            item.setEnabled(page == "room")
            item.highlighted = False
            item.clearFocus()
        for item in self.device_hotspots.values():
            item.setVisible(page == "desk")
            item.setEnabled(page == "desk")
            item.setPen(QPen(QColor(0, 0, 0, 0), 0))
            item.highlighted = False
            item.clearFocus()
        self._hover(None)
        self.blur.setBlurRadius(0 if page in ("room", "desk", "desk_transition") else 16)
        self.shade.setBrush(QColor(0, 0, 0, 0 if page in ("room", "desk", "desk_transition") else 115))
        self._apply_hover_help()
        if page=='device':self._device_started=self._play_clock()
        self.page_changed.emit(page)

    def start_game(self):
        if self.page != "menu":
            return
        self._show_page("transition")
        if self.animation_ms:
            self.transition.start()
        else:
            self._finish_start()

    def _finish_start(self):
        if self.journey.should_offer_tutorial and not self._has_prior_play:
            self.open_tutorial(automatic=True)
        else:self._show_page('room')

    def open_tutorial(self,*,automatic=False):
        if self.controller is not None:self.controller.stop()
        if self.tutorial_panel is None:
            from .tutorial import TutorialPanel
            self.tutorial_panel=TutorialPanel(self.journey,language=self.language,volume=self.preferences.volume/100)
            self.tutorial_panel.finished.connect(self._tutorial_finished)
            self.tutorial_proxy=self._proxy(self.tutorial_panel,50,90,1180,610)
            self.volume_changed.connect(self.tutorial_panel.set_volume)
        self._tutorial_return='room' if automatic else self.page if self.page in ('menu','room','device','desk') else 'menu'
        self.tutorial_panel.start(replay=not automatic)
        self._show_page('tutorial')

    def _tutorial_finished(self,completed):
        self._show_page('room' if completed else self._tutorial_return)
        if completed:
            self.board.open(self.preferences.active_case,self.language,free_composition=self.free_composition)
            self._show_page('board')

    def _flush_device_time(self):
        if self._device_started is not None and self.controller is not None:
            key=self.controller.case.id
            store=self._case_journey()
            timing=store.timings.setdefault(key,{'seconds':0.,'complete':False})
            timing['seconds']+=max(0.,self._play_clock()-self._device_started)
            self._device_started=None
            store.save()

    def _case_journey(self):
        difficulty=getattr(getattr(self.controller,'case',None),'difficulty','advanced')
        if difficulty=='advanced':return self.journey
        key=self.controller.case.id+'-'+difficulty
        if key not in self.source_journeys:
            self.source_journeys[key]=JourneyStore(self.progress_dir/'wordle/levels'/f'{key}-journey.json')
        return self.source_journeys[key]

    def _source_difficulty_changed(self):
        store=self._case_journey();key=self.controller.case.id
        store.timings.setdefault(key,{'seconds':0.,'complete':self.controller.session.attempts==0})
        self.room_review.setEnabled(self._review_available())
        if self.page=='device':self._device_started=self._play_clock()

    def open_cabinet(self):
        if self.cabinet_panel is None:
            from .evidence import EvidencePanel
            self.cabinet_panel=EvidencePanel(self.evidence_store,(*self.cases,self.board.wordle,*self.board.melody_cases.values(),*self.board.source_cases),language=self.language,volume=self.preferences.volume/100)
            self.cabinet_panel.back_requested.connect(lambda:self._show_page(self._cabinet_return))
            self.cabinet_proxy=self._proxy(self.cabinet_panel,50,90,1180,610)
            self.volume_changed.connect(self.cabinet_panel.set_volume)
        self._cabinet_return=self.page if self.page in ('room','desk','device') else 'room'
        self.cabinet_panel.refresh();self._show_page('cabinet')

    def _review_available(self):
        if self.controller is None or self.free_composition:return False
        session=self.controller.session
        return self.controller.case.id in self._case_journey().reviews or bool(session.solved or getattr(session,'first_pass',None))

    def _on_case_completed(self,controller):
        if self._closed or controller is not self.controller:return
        self._flush_device_time()
        from ..game.debrief import build_debrief
        store=self._case_journey()
        timing=store.timings.get(controller.case.id,{})
        seconds=timing.get('seconds') if timing.get('complete') else None
        record=store.remember(build_debrief(controller.case,controller.session,seconds=seconds))
        if record.kind!='music' and record.clips['final'] is not None:
            self.evidence_store.remember(record,getattr(controller.case,'difficulty','advanced'))
        self.room_review.setEnabled(True)
        if not controller.case.id.startswith('M'):
            completed_current=controller.session.current
            completed_case=controller.case
            # A rapid edit after submitting should keep the player at the desk.
            QTimer.singleShot(0,lambda:self.open_review() if not self._closed and self.controller is controller
                and controller.case is completed_case and self.page=='device' and controller.session.current==completed_current else None)

    def open_review(self):
        if not self._review_available():return False
        self._flush_device_time()
        controller=self.controller
        from ..game.debrief import build_debrief
        store=self._case_journey()
        record=store.reviews.get(controller.case.id)
        if record is None:record=store.remember(build_debrief(controller.case,controller.session))
        if self.debrief_panel is None:
            from .debrief import DebriefPanel
            self.debrief_panel=DebriefPanel(language=self.language,volume=self.preferences.volume/100)
            self.debrief_panel.back_requested.connect(self._leave_review)
            self.debrief_panel.cases_requested.connect(self._review_cases)
            self.debrief_proxy=self._proxy(self.debrief_panel,50,90,1180,610)
            self.volume_changed.connect(self.debrief_panel.set_volume)
        controller.stop()
        self._review_return=self.page if self.page in ('room','desk','device') else 'device'
        self.debrief_panel.load(record,controller.case)
        self._show_page('review')
        return True

    def _leave_review(self):self._show_page(self._review_return)

    def _review_cases(self):
        self.board.open(self.preferences.active_case,self.language,free_composition=self.free_composition)
        self._show_page('board')

    def _animate_room(self, value):
        self.blur.setBlurRadius(16 * (1 - value))
        self.shade.setBrush(QColor(0, 0, 0, int(115 * (1 - value))))

    def _hover(self, key):
        self._hovered = key
        hint = "desk_help" if self.page == "desk" else "room_help"
        if self.scene_key == "music":
            hint = f"{'composition' if self.free_composition else 'music'}_{hint}"
        self.caption.setText(self._device_label(key) if key else TEXT[self.language][hint])

    def _device_label(self, key):
        if key in ("desk", "board") and self.free_composition:
            key = f"composition_{key}"
        elif key in ("synth", "delay", "reverb", "analyzer", "desk", "board") and (self.preferences.active_case or "").startswith("M"):
            key = f"music_{key}"
        elif key == "synth" and self.preferences.active_case in MELODY_IDS:
            key = "melody_synth"
        elif key == "synth" and self.preferences.active_case == "W01":
            key = "wordle_synth"
        elif key == "synth" and self.preferences.active_case in ("W03","W04","W05","W06"):
            key = "source_synth"
        return TEXT[self.language][key]

    def _activate_hotspot(self, key):
        if self.page == "room":
            play_widget_click(self, key)
            self.hotspot_activated.emit(key)
            if key == "board":
                self.board.open(self.preferences.active_case, self.language, free_composition=self.free_composition)
                self._show_page("board")
            else:
                if self.animation_ms:
                    self._show_page("desk_transition")
                    self.desk_transition.start()
                else:
                    self._show_page("desk")

    def _accept_case(self, case_id):
        if not self._load_case(case_id):
            self.board.note.setText(TEXT[self.language]["case_error"])
            return False
        self.preferences.active_case = case_id
        if case_id in MELODY_IDS:
            self.controller._set_mode("challenge")
        self._save_preferences()
        self.room_title.setText(f"SOUND DETECTIVE  /  {case_id}")
        self._show_page("room")
        return True

    def open_music_studio(self):
        """Resume the authored music case in its dedicated room."""
        return self.music is not None and self._accept_case(self.music.id)

    def open_free_composition(self):
        if not self._load_case("W02"):
            self.board.note.setText(TEXT[self.language]["case_error"])
            return False
        self.preferences.active_case = "W02"
        self.controller._set_mode("free")
        self._save_preferences()
        self._show_page("room")
        return True

    def _melody_mode_changed(self, mode):
        if self.preferences.active_case == "W02" and self.controller and self.controller.case.id == "W02":
            self._show_page(self.page)

    def _load_case(self, case_id):
        if self.controller and self.controller.case.id == case_id:
            return True
        from .device_panel import ToneDevicePanel, MusicDevicePanel
        try:
            if case_id.startswith("T"):
                case = next(case for case in self.cases if case.id == case_id)
                candidate = (self._tone_factory or ToneDevicePanel)(case=case, save_path=self.progress_dir / f"{case_id}.json")
            elif case_id == "W01":
                from .hidden_sound import HiddenSoundWindow
                candidate = (self._wordle_factory or HiddenSoundWindow)(case=self.board.wordle,
                    save_path=self.progress_dir / "wordle/W01.json", language=self.language,
                    volume=self.preferences.volume / 100, embedded=True)
                candidate.device_requested.connect(self._wordle_device)
            elif case_id in MELODY_IDS:
                from .melody import MelodyWindow
                candidate = (self._melody_factory or MelodyWindow)(case=self.board.melody_cases[case_id],
                    save_path=self.progress_dir / "wordle"/(case_id+'.json'), language=self.language,
                    volume=self.preferences.volume / 100, embedded=True)
                candidate.device_requested.connect(self._wordle_device)
                candidate.mode_changed.connect(self._melody_mode_changed)
            elif case_id in ("W03","W04","W05","W06"):
                from .sound_categories import SourceCaseWindow
                case = next(case for case in self.board.source_cases if case.id == case_id)
                candidate = SourceCaseWindow(case=case,
                    save_path=self.progress_dir / "wordle" / f"{case_id}.json",
                    language=self.language, volume=self.preferences.volume/100, embedded=True,difficulty=None)
                candidate.device_requested.connect(self._wordle_device)
            else:
                if self.music is None or self.music.id != case_id:
                    return False
                self.music.verify_assets()
                candidate = (self._music_factory or MusicDevicePanel)(case=self.music,
                    save_path=self.progress_dir / "music" / f"{case_id}.json", language=self.language, volume=self.preferences.volume / 100)
                candidate.device_requested.connect(self._music_device)
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, StopIteration):
            return False
        if self.controller:
            self._flush_device_time()
            self.controller.close()
            self.controller.deleteLater()
        if self.device_proxy:
            self.device_proxy.hide()
            self.view.scene().removeItem(self.device_proxy)
            self.device_proxy.deleteLater()
        self.controller = candidate
        if hasattr(candidate,'difficulty_changed'):
            candidate.difficulty_changing.connect(self._flush_device_time)
            candidate.difficulty_changed.connect(self._source_difficulty_changed)
        candidate.setProperty('studioEmbedded',True)
        if hasattr(candidate,'case_completed'):
            candidate.case_completed.connect(lambda c=candidate:self._on_case_completed(c))
        if hasattr(candidate,'review_requested'):candidate.review_requested.connect(self.open_review)
        self._case_journey().timings.setdefault(case_id,{'seconds':0.,'complete':getattr(candidate.session,'attempts',0)==0})
        candidate.setParent(self)
        candidate.setStyleSheet(STYLE)
        candidate.hide()
        candidate.language.setCurrentIndex(0 if self.language == "en" else 1)
        candidate.volume.setValue(self.preferences.volume)
        if hasattr(candidate, "_clock_timer"):
            candidate._clock_timer.stop()
        body = candidate.takeCentralWidget()
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)
        self.device_proxy = self._proxy(frame, 50, 90, 1180, 610)
        self.device_proxy.hide()
        return True

    def _wordle_device(self, device):
        if self.page == "device" and (self.preferences.active_case or "").startswith("W"):
            self.current_device = device
            self.controller.present_device(device)
            self._show_page("device")

    def _music_device(self, device):
        if self.page == "device" and (self.preferences.active_case or "").startswith("M"):
            self.current_device = device
            self.controller.present_device(device)
            self._show_page("device")

    def _activate_device(self, key):
        if self.page != "desk":
            return
        if self.preferences.active_case is None:
            self.caption.setText(TEXT[self.language]["choose_case"])
            return
        play_widget_click(self, f"device_{key}")
        self.hotspot_activated.emit(key)
        if not self._load_case(self.preferences.active_case):
            self.caption.setText(TEXT[self.language]["case_error"])
            return
        self.current_device = key
        self.controller.present_device(key)
        self._show_page("device")
        if hasattr(self.controller, "_clock_timer"):
            self.controller._clock_timer.start()

    def go_back(self):
        if self.page=='tutorial':self.tutorial_panel.skip()
        elif self.page=='cabinet':self._show_page(self._cabinet_return)
        elif self.page=='review':self._leave_review()
        elif self.page == "settings":
            self.close_settings()
        elif self.page in ("board", "desk"):
            self._show_page("room")
        elif self.page == "device":
            self._show_page("desk")
        elif self.page == "room":
            self._show_page("menu")

    def _sizes(self):
        area = self.screen().availableGeometry()
        return window_sizes(area.width(), area.height())

    def open_settings(self):
        if self.page not in ("menu", "room", "desk", "device","tutorial","review","cabinet"):
            return
        self._settings_return = self.page
        self.size_combo.clear()
        for width, height in self._sizes():
            self.size_combo.addItem(f"{width} × {height}", (width, height))
        index = next((i for i in range(self.size_combo.count())
                      if tuple(self.size_combo.itemData(i) or ()) == (self.width(), self.height())), -1)
        if index < 0:
            self.size_combo.insertItem(0, f"{self.width()} × {self.height()}", None)
            self.size_combo.setItemEnabled(0, False)
            index = 0
        self.size_combo.setCurrentIndex(max(0, index))
        self._show_page("settings")

    def close_settings(self):
        self._show_page(self._settings_return)

    def open_diagnostics(self):
        from .diagnostics import DiagnosticsDialog
        if self.controller:
            self.controller.stop()
        if self.tutorial_panel is not None:self.tutorial_panel.stop()
        if self.debrief_panel is not None:self.debrief_panel.stop()
        if self.cabinet_panel is not None:self.cabinet_panel.stop()
        dialog = DiagnosticsDialog(self, language=self.language)
        dialog.exec()

    def _size_changed(self, index):
        size = self.size_combo.itemData(index)
        if size:
            if self.isMaximized() or self.isFullScreen():
                self.showNormal()
            self.resize(*size)
            self.preferences.width, self.preferences.height = size
            self._save_preferences()

    def _volume_changed(self, value):
        self.preferences.volume = value
        self.setProperty("uiAudioVolume", value / 100)
        for item in self.view.scene().items():
            if hasattr(item, "widget") and item.widget() is not None:
                item.widget().setProperty("uiAudioVolume", value / 100)
        bus = ui_sounds(create=False)
        if bus is not None:
            bus.set_volume(value / 100)
        self.volume_label.setText(f"{value}%")
        self.volume_changed.emit(value / 100)
        if self.controller:
            self.controller.volume.setValue(value)
        self._save_preferences()

    def _language_changed(self, index):
        self.preferences.language = self.language_combo.itemData(index)
        self._translate()
        self._save_preferences()

    def _save_preferences(self):
        try:
            self.store.save(self.preferences)
        except (OSError, ValueError):
            self.store.warning = "save_error"
        self.warning.setText(TEXT[self.language].get(self.store.warning, ""))
        self.warning_proxy.setVisible(bool(self.store.warning))

    def keyPressEvent(self, event):
        if (self.page == 'device' and self.controller and hasattr(self.controller, 'edit_bar')
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and not event.modifiers() & Qt.KeyboardModifier.AltModifier
                and event.key() in (Qt.Key.Key_Z, Qt.Key.Key_Y)):
            redo = event.key() == Qt.Key.Key_Y or bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.controller.edit_bar.redo() if redo else self.controller.edit_bar.undo()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            if self.page=='tutorial':self.tutorial_panel.stop()
            elif self.page=='cabinet':self.cabinet_panel.stop()
            elif self.page=='review':self.debrief_panel.stop()
            elif self.controller and self.page == "device":
                self.controller.stop()
            else:
                self.go_back()
            event.accept()
        else:
            super().keyPressEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowDeactivate and hasattr(self, "tutorial_panel"):
            QTimer.singleShot(0, self._check_focus)
        elif event.type()==QEvent.Type.ActivationChange and hasattr(self,'page') and self.isActiveWindow() and self.page=='device' and self._device_started is None:
            self._device_started=self._play_clock()

    def _check_focus(self):
        if self._closed or self.isActiveWindow() or QApplication.activePopupWidget():
            return
        self._flush_device_time()
        if self.tutorial_panel is not None:self.tutorial_panel.stop()
        if self.debrief_panel is not None:self.debrief_panel.stop()
        if self.cabinet_panel is not None:self.cabinet_panel.stop()
        if self.controller and not (self.preferences.active_case.startswith("M") and self.controller.session.solved):
            self.controller.stop()

    def closeEvent(self, event):
        if not self._closed:
            self._flush_device_time()
            self._exit_timer.stop()
            self.transition.stop()
            self.desk_transition.stop()
            if self.controller:
                self.controller.close()
            if self.tutorial_panel is not None:self.tutorial_panel.shutdown()
            if self.debrief_panel is not None:self.debrief_panel.shutdown()
            if self.cabinet_panel is not None:self.cabinet_panel.shutdown()
            for store in self.source_journeys.values():store.save()
            self.journey.save()
            self._save_preferences()
            self._closed = True
        event.accept()

    def _exit_after_click(self):
        wait = remaining_click_ms()
        if wait > 0:
            self.exit_button.setEnabled(False)
            self._exit_timer.start(wait + 8)
        else:
            self.close()
