import argparse
import os
import sys
import traceback
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="心光 · 离线激励语录")
    parser.add_argument("--smoke-test", metavar="OUTPUT_DIR", help=argparse.SUPPRESS)
    parser.add_argument("--native", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    native_qa = args.native or os.name == "nt"
    if args.smoke_test and not native_qa:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QApplication, QMessageBox
    from xinguang.catalog import Catalog
    from xinguang.favorites import FavoritesStore
    from xinguang.ui import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("XinGuang")
    app.setApplicationDisplayName("心光")
    app.setOrganizationName("XinGuang")
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(not bool(args.smoke_test))
    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    if args.smoke_test:
        data_dir = Path(args.smoke_test).resolve() / "user-data"

    def report_error(exc_type, value, trace):
        details = "".join(traceback.format_exception(exc_type, value, trace))
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            (data_dir / "error.log").write_text(details, encoding="utf-8")
        except OSError:
            pass
        if args.smoke_test:
            target = Path(args.smoke_test).resolve()
            target.mkdir(parents=True, exist_ok=True)
            (target / "failure.txt").write_text(details, encoding="utf-8")
            app.exit(1)
        else:
            QMessageBox.critical(None, "心光", "软件遇到了一个问题，请尝试重新打开。\n\n" + str(value))

    sys.excepthook = report_error
    try:
        catalog = Catalog()
        catalog.validate_files()
        store = FavoritesStore(data_dir / "favorites.json", set(catalog.by_id))
        window = MainWindow(catalog, store)
        if args.smoke_test:
            from xinguang.smoke import run_smoke
            run_smoke(app, window, Path(args.smoke_test).resolve(), native=native_qa)
        else:
            screen = app.primaryScreen()
            available = screen.availableGeometry()
            window.resize(min(1100, available.width() - 40), min(720, available.height() - 60))
            window.move(available.center() - window.rect().center())
            window.show()
        return app.exec()
    except Exception:
        report_error(*sys.exc_info())
        return 1


if __name__ == "__main__":
    sys.exit(main())
