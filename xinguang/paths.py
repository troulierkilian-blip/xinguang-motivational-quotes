from pathlib import Path


def resource_path(relative: str) -> Path:
    # PyInstaller preserves __file__ relative to the extracted bundle.
    return Path(__file__).resolve().parent.parent / "assets" / relative
