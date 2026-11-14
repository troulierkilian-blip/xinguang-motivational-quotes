from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve, Property, QPropertyAnimation, QRectF, Qt,
    QSequentialAnimationGroup, QTimer, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QIcon, QKeySequence, QLinearGradient,
    QPainter, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .catalog import Catalog
from .engine import QuoteEngine, Scene
from .favorites import FavoritesStore
from .paths import resource_path


def make_font(size: int, weight=QFont.Weight.Normal) -> QFont:
    result = QFont("Microsoft YaHei UI", size)
    result.setWeight(weight)
    return result


def label(text: str, size: int, color: str = "#f5f1e9", bold=False) -> QLabel:
    result = QLabel(text)
    result.setFont(make_font(size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal))
    result.setStyleSheet(f"color: {color}; background: transparent; border: none;")
    return result


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI'; color: #f5f1e9; }
QPushButton { border: 1px solid rgba(240,225,194,42); border-radius: 12px;
    padding: 10px 18px; color: #ede8dc; background: rgba(13,25,32,95); font-size: 14px; }
QPushButton:hover { background: rgba(236,213,172,30); border-color: rgba(240,225,194,100); }
QPushButton:pressed { background: rgba(236,213,172,48); }
QPushButton:focus { border: 2px solid #efd39c; }
QPushButton:disabled { color: rgba(237,232,220,105); }
QPushButton#primary { background: #e9c78b; color: #263238; border: 1px solid #f4d9a9;
    font-size: 16px; font-weight: 600; border-radius: 13px; }
QPushButton#primary:hover { background: #f4d9a9; }
QPushButton#primary:pressed { background: #d6b071; }
QPushButton#primary:disabled { background: #bdab87; color: #4b514e; }
QPushButton#quiet { background: transparent; border-color: transparent; color: #d3cfc4; }
QPushButton#quiet:hover { background: rgba(245,228,195,25); color: #ffdda0; }
QFrame#quoteCard { background: rgba(12,24,32,174); border: 1px solid rgba(240,225,194,55);
    border-radius: 25px; }
QDialog { background: #14252e; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 3px; }
QScrollBar::handle:vertical { background: #5b6461; border-radius: 3px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


class BackgroundCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self._current = QPixmap()
        self._old = QPixmap()
        self._mix = 1.0
        self._cache = OrderedDict()
        self.animation = QPropertyAnimation(self, b"mix", self)
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._discard_old)

    def get_mix(self):
        return self._mix

    def set_mix(self, value):
        self._mix = value
        self.update()

    mix = Property(float, get_mix, set_mix)

    def _discard_old(self):
        self._old = QPixmap()

    def set_background(self, path: Path, animate: bool):
        key = str(path)
        if key not in self._cache:
            pixmap = QPixmap(key)
            if pixmap.isNull():
                raise ValueError(f"无法读取背景：{path.name}")
            self._cache[key] = pixmap
        self._cache.move_to_end(key)
        while len(self._cache) > 3:
            self._cache.popitem(last=False)
        self.animation.stop()
        self._old = self._current if animate else QPixmap()
        self._current = self._cache[key]
        if animate and not self._old.isNull():
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        else:
            self.set_mix(1.0)
        self.update()

    def _draw_cover(self, painter: QPainter, pixmap: QPixmap):
        if pixmap.isNull():
            return
        scale = max(self.width() / pixmap.width(), self.height() / pixmap.height())
        sw, sh = self.width() / scale, self.height() / scale
        source = QRectF((pixmap.width() - sw) / 2, (pixmap.height() - sh) / 2, sw, sh)
        painter.drawPixmap(QRectF(self.rect()), pixmap, source)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#14252e"))
        if not self._old.isNull() and self._mix < 1:
            self._draw_cover(painter, self._old)
            painter.setOpacity(self._mix)
        self._draw_cover(painter, self._current)
        painter.setOpacity(1)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(6, 16, 24, 65))
        gradient.setColorAt(.42, QColor(6, 16, 24, 18))
        gradient.setColorAt(1, QColor(6, 16, 24, 135))
        painter.fillRect(self.rect(), gradient)


class FavoritesDialog(QDialog):
    changed = Signal()

    def __init__(self, catalog: Catalog, store: FavoritesStore, parent):
        super().__init__(parent)
        self.catalog, self.store = catalog, store
        self.setWindowTitle("我的收藏 · 心光")
        self.setWindowIcon(QIcon(str(resource_path("logo.svg"))))
        self.setStyleSheet(STYLE)
        self.resize(680, 550)
        self.setMinimumSize(530, 380)
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 24)
        root.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(label("留住心里的光", 21, bold=True))
        top.addStretch()
        self.count_label = label("", 10, "#bfbeb1")
        top.addWidget(self.count_label)
        root.addLayout(top)
        root.addWidget(label("喜欢的话，值得再读一次。", 10, "#bfbeb1"))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)
        self.message = label("", 10, "#e9c78b")
        self.message.setWordWrap(True)
        root.addWidget(self.message)
        close = QPushButton("返回语录")
        close.setFixedWidth(130)
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        root.addLayout(row)
        self.rebuild()

    def rebuild(self):
        self.count_label.setText(f"{len(self.store.ids)} 句收藏")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)
        if not self.store.ids:
            layout.addStretch()
            empty = label("把喜欢的话，留在这里。", 17, "#e9c78b")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
            hint = label("点击语录下方的「收藏这句」，下次仍能找到它。", 10, "#bfbeb1")
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)
            layout.addStretch()
        else:
            for quote_id in self.store.ids:
                quote = self.catalog.by_id[quote_id]
                frame = QFrame()
                frame.setStyleSheet("QFrame { background: #1e333d; border: 1px solid #3a4a4f; border-radius: 14px; }")
                content = QVBoxLayout(frame)
                content.setContentsMargins(18, 16, 18, 12)
                text = label(quote.text, 13)
                text.setWordWrap(True)
                text.setTextFormat(Qt.TextFormat.PlainText)
                content.addWidget(text)
                row = QHBoxLayout()
                row.addWidget(label(self.catalog.themes[quote.theme].name, 10, "#e9c78b"))
                row.addStretch()
                copy = QPushButton("复制")
                copy.setObjectName("quiet")
                copy.clicked.connect(lambda checked=False, q=quote: self.copy_text(q.text))
                remove = QPushButton("取消收藏")
                remove.setObjectName("quiet")
                remove.clicked.connect(lambda checked=False, qid=quote_id: self.remove(qid))
                row.addWidget(copy)
                row.addWidget(remove)
                content.addLayout(row)
                layout.addWidget(frame)
            layout.addStretch()
        previous = self.scroll.takeWidget()
        if previous:
            previous.deleteLater()
        self.scroll.setWidget(container)

    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        self.message.setText("已复制，可以粘贴分享。")

    def remove(self, quote_id):
        try:
            self.store.toggle(quote_id)
        except OSError:
            self.message.setText("收藏未能保存，请检查用户目录的写入权限。")
            return
        self.rebuild()
        self.changed.emit()
        self.message.setText("已取消收藏。")


class MainWindow(BackgroundCanvas):
    def __init__(self, catalog: Catalog, store: FavoritesStore, engine=None):
        super().__init__()
        self.catalog, self.store = catalog, store
        self.engine = engine or QuoteEngine(catalog)
        self.current_scene: Scene | None = None
        self.busy = False
        self._display_count = 0
        self.setWindowTitle("心光 · 激励语录")
        self.setWindowIcon(QIcon(str(resource_path("logo.svg"))))
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
        self.setStyleSheet(STYLE)
        self._build_layout()
        self._show_initial()
        self._setup_shortcuts()
        if store.warning:
            QTimer.singleShot(600, lambda: self.toast(store.warning))

    def _build_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(46, 30, 46, 24)
        root.setSpacing(0)
        header = QHBoxLayout()
        brand = QLabel()
        brand.setPixmap(QIcon(str(resource_path("logo.svg"))).pixmap(44, 44))
        brand.setFixedSize(44, 44)
        header.addWidget(brand)
        name = QVBoxLayout()
        name.setSpacing(1)
        name.addWidget(label("心 光", 22, bold=True))
        name.addWidget(label("给今天一点向前的光", 10, "#deded2"))
        header.addSpacing(10)
        header.addLayout(name)
        header.addStretch()
        self.list_button = QPushButton("我的收藏   0")
        self.list_button.setAccessibleName("打开我的收藏")
        self.list_button.clicked.connect(self.open_favorites)
        header.addWidget(self.list_button)
        root.addLayout(header)
        root.addStretch(2)

        self.card = QFrame()
        self.card.setObjectName("quoteCard")
        self.card.setMaximumWidth(820)
        card = QVBoxLayout(self.card)
        card.setContentsMargins(40, 26, 40, 26)
        card.setSpacing(16)
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        words = QVBoxLayout(self.content)
        words.setContentsMargins(0, 0, 0, 0)
        words.setSpacing(9)
        self.theme_label = label("", 10, "#ebc98b")
        self.theme_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_font = self.theme_label.font()
        caption_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        self.theme_label.setFont(caption_font)
        words.addWidget(self.theme_label)
        mark = label("“", 40, "#e9c78b")
        mark.setFixedHeight(52)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        words.addWidget(mark)
        self.quote_label = label("", 24)
        self.quote_label.setWordWrap(True)
        self.quote_label.setMinimumHeight(110)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setTextFormat(Qt.TextFormat.PlainText)
        self.quote_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        words.addWidget(self.quote_label)
        origin = label("—  心光原创", 10, "#bfc4bd")
        origin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        words.addWidget(origin)
        self.opacity = QGraphicsOpacityEffect(self.content)
        self.content.setGraphicsEffect(self.opacity)
        card.addWidget(self.content)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(235,217,182,38); border: none;")
        card.addWidget(line)
        actions = QHBoxLayout()
        actions.setSpacing(16)
        actions.addStretch()
        self.copy_button = QPushButton("复制语录")
        self.copy_button.setObjectName("quiet")
        self.copy_button.clicked.connect(self.copy_current)
        self.next_button = QPushButton("换一句   →")
        self.next_button.setObjectName("primary")
        self.next_button.setFixedSize(184, 50)
        self.next_button.setAccessibleName("更换一条新的激励语录和背景")
        self.next_button.clicked.connect(self.next_quote)
        self.favorite_button = QPushButton("收藏这句")
        self.favorite_button.setObjectName("quiet")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.next_button)
        actions.addWidget(self.favorite_button)
        actions.addStretch()
        card.addLayout(actions)
        center = QHBoxLayout()
        center.addStretch()
        center.addWidget(self.card, 1)
        center.addStretch()
        root.addLayout(center)
        root.addStretch(3)

        self.toast_label = label("", 10, "#ffe1a7")
        self.toast_label.setMinimumHeight(22)
        self.toast_label.setWordWrap(True)
        self.toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.toast_label)
        root.addSpacing(12)
        footer = QHBoxLayout()
        footer.addWidget(label("一步一步，向光而行。", 10, "#d4d7cf"))
        footer.addStretch()
        footer.addWidget(label("空格键 · 换一句     |     离线可用 · 180 句", 9, "#c4cec7"))
        root.addLayout(footer)
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(lambda: self.toast_label.setText(""))

    def _setup_shortcuts(self):
        for sequence, callback in (("Space", self.next_quote), ("Ctrl+C", self.copy_current),
                                   ("Ctrl+D", self.toggle_favorite), ("Ctrl+L", self.open_favorites)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setAutoRepeat(False)
            shortcut.activated.connect(callback)

    def _show_initial(self):
        scene = self.engine.next()
        self.set_background(scene.background, False)
        self.set_words(scene)
        self.opacity.setOpacity(1)
        self.update_favorite_state()

    def set_words(self, scene):
        self.current_scene = scene
        theme = self.catalog.themes[scene.quote.theme]
        self.theme_label.setText(f"{theme.name}  ·  {theme.english}")
        self.quote_label.setText(scene.quote.text)
        self._display_count += 1

    def next_quote(self):
        if self.busy:
            return
        scene = self.engine.next()
        try:
            self.set_background(scene.background, True)
        except ValueError as error:
            self.toast(str(error))
            return
        self.busy = True
        for button in (self.next_button, self.copy_button, self.favorite_button, self.list_button):
            button.setEnabled(False)
        self.toast_label.setText("")
        self.transition = QSequentialAnimationGroup(self)
        out = QPropertyAnimation(self.opacity, b"opacity")
        out.setDuration(160)
        out.setStartValue(1)
        out.setEndValue(0)
        out.finished.connect(lambda: self.set_words(scene))
        inside = QPropertyAnimation(self.opacity, b"opacity")
        inside.setDuration(240)
        inside.setStartValue(0)
        inside.setEndValue(1)
        self.transition.addAnimation(out)
        self.transition.addAnimation(inside)
        self.transition.finished.connect(self._transition_done)
        self.transition.start()

    def _transition_done(self):
        self.busy = False
        for button in (self.next_button, self.copy_button, self.favorite_button, self.list_button):
            button.setEnabled(True)
        self.update_favorite_state()
        self.transition.deleteLater()

    def copy_current(self):
        if not self.busy and self.current_scene:
            QApplication.clipboard().setText(self.current_scene.quote.text)
            self.toast("已复制，可以粘贴分享。")

    def toggle_favorite(self):
        if self.busy or not self.current_scene:
            return
        try:
            added = self.store.toggle(self.current_scene.quote.id)
        except OSError:
            self.toast("收藏未能保存，请检查用户目录的写入权限。")
            return
        self.update_favorite_state()
        self.toast("已收藏，把这束光留给下一次。" if added else "已取消收藏。")

    def update_favorite_state(self):
        selected = self.current_scene and self.store.contains(self.current_scene.quote.id)
        self.favorite_button.setText("已收藏 ✓" if selected else "收藏这句")
        self.favorite_button.setStyleSheet("color: #f3cf8f;" if selected else "")
        self.list_button.setText(f"我的收藏   {len(self.store.ids)}")

    def open_favorites(self):
        if not self.busy:
            dialog = FavoritesDialog(self.catalog, self.store, self)
            dialog.changed.connect(self.update_favorite_state)
            dialog.exec()
            dialog.deleteLater()

    def toast(self, text):
        self.toast_label.setText(text)
        self.toast_timer.start(4500)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "quote_label"):
            self.quote_label.setFont(make_font(24 if self.width() >= 1000 else 21))
