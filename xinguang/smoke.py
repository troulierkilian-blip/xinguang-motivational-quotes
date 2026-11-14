"""Deterministic executable smoke check, isolated from the user's favorites."""
import json
import platform
import random
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QMimeData, QRect, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QImage
from PySide6.QtWidgets import QApplication

from .engine import QuoteEngine, Scene
from .favorites import FavoritesStore
from .ui import FavoritesDialog


def run_smoke(app, window, output: Path, native=False):
    output.mkdir(parents=True, exist_ok=True)
    report = {"platform": platform.platform(), "python": sys.version,
              "frozen": bool(getattr(sys, "frozen", False)),
              "qt_platform": app.platformName(), "checks": [], "images": []}
    clipboard_backup = QMimeData()
    original = app.clipboard().mimeData()
    if original is not None:
        for mime in original.formats():
            clipboard_backup.setData(mime, original.data(mime))

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report["checks"].append(name)

    def capture(widget, filename):
        check("capture:" + filename, widget.grab().save(str(output / filename)))
        report["images"].append(filename)

    def guarded(callback):
        def wrapper():
            try:
                callback()
            except Exception:
                report["status"] = "failed"
                report["error"] = traceback.format_exc()
                finish(1)
        return wrapper

    def later(callback, delay=150):
        QTimer.singleShot(delay, guarded(callback))

    def finish(code=0):
        app.clipboard().setMimeData(clipboard_backup)
        if code == 0:
            report["status"] = "passed"
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(code)

    def audit_layout():
        metrics = QFontMetrics(window.quote_label.font())
        available = window.quote_label.contentsRect()
        for quote in window.catalog.quotes:
            bounds = metrics.boundingRect(QRect(0, 0, available.width(), 10000),
                                           int(Qt.TextFlag.TextWordWrap), quote.text)
            check("text-fits:" + quote.id, bounds.height() <= available.height())
        check("button-visible", window.next_button.isVisible())
        check("card-fits", window.rect().contains(window.card.geometry()))

    def initial():
        sizes = []
        for theme in window.catalog.themes.values():
            for path in theme.backgrounds:
                image = QImage(str(path))
                check("image-decodes:" + path.name, not image.isNull())
                check("landscape:" + path.name, image.width() > image.height())
                sizes.append([path.name, image.width(), image.height()])
        report["backgrounds"] = sizes
        engine = QuoteEngine(window.catalog, random.Random(741))
        scenes = [engine.next() for _ in range(540)]
        for start in (0, 180, 360):
            check("shuffle-round:" + str(start), len({s.quote.id for s in scenes[start:start + 180]}) == 180)
        check("no-adjacent-quotes", all(a.quote.id != b.quote.id for a, b in zip(scenes, scenes[1:])))
        check("background-always-changes", all(a.background != b.background for a, b in zip(scenes, scenes[1:])))
        check("background-theme-match", all(s.background in window.catalog.themes[s.quote.theme].backgrounds for s in scenes))
        # Native QA windows are rendered without taking over the user's screen.
        if native:
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        scene = Scene(window.catalog.by_id["hope_01"], window.catalog.themes["hope"].backgrounds[0])
        window.set_background(scene.background, False)
        window.set_words(scene)
        window.update_favorite_state()
        window.show()
        later(normal)

    before = {}

    def normal():
        audit_layout()
        capture(window, "main.png")
        window.copy_current()
        check("copy-current", app.clipboard().text() == window.current_scene.quote.text)
        qid = window.current_scene.quote.id
        if window.store.contains(qid):
            window.store.toggle(qid)
        window.toggle_favorite()
        check("favorite-added", window.store.contains(qid))
        reopened = FavoritesStore(window.store.path, set(window.catalog.by_id))
        check("favorites-restored", reopened.contains(qid))
        before.update(id=qid, background=window.current_scene.background, count=window._display_count)
        # Simulate an actual button click followed by a rapid burst.
        window.next_button.click()
        for _ in range(30):
            window.next_quote()
        check("animation-busy", window.busy)
        later(changed, 700)

    def changed():
        # Windows pauses visual animation clocks for an unexposed QA window.
        # Drive both timelines to the end to verify their actual finished slots.
        if native and window.busy:
            window.animation.setCurrentTime(window.animation.duration())
            window.transition.setCurrentTime(window.transition.duration())
            report["checks"].append("hidden-window-animation-timeline-driven")
        check("animation-complete", not window.busy)
        check("quote-changed", window.current_scene.quote.id != before["id"])
        check("scene-changed", window.current_scene.background != before["background"])
        check("rapid-clicks-coalesced", window._display_count == before["count"] + 1)
        capture(window, "after-switch.png")
        window.resize(800, 560)
        later(small)

    def small():
        audit_layout()
        capture(window, "small.png")
        window.resize(1300, 850)
        later(large)

    def large():
        audit_layout()
        capture(window, "large.png")
        dialog = FavoritesDialog(window.catalog, window.store, window)
        if native:
            dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        dialog.show()
        window._qa_dialog = dialog
        later(favorites)

    def favorites():
        dialog = window._qa_dialog
        capture(dialog, "favorites.png")
        qid = before["id"]
        check("favorite-in-list", window.store.contains(qid))
        dialog.copy_text(window.catalog.by_id[qid].text)
        check("copy-favorite", app.clipboard().text() == window.catalog.by_id[qid].text)
        dialog.remove(qid)
        check("favorite-removed", not window.store.contains(qid))
        check("removal-restored", not FavoritesStore(window.store.path, set(window.catalog.by_id)).contains(qid))
        capture(dialog, "favorites-empty.png")
        dialog.close()
        finish()

    later(initial, 0)
