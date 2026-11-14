# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'assets'), 'assets')],
    hiddenimports=['PySide6.QtSvg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtMultimedia',
              'PySide6.Qt3DCore', 'tkinter', 'unittest'],
    noarchive=False,
)
# Use the operating system UCRT, not an older copy found on a build host's PATH.
# Keep the C++ runtimes consistent with the Qt wheels.
qt_dir = root / '.venv' / 'Lib' / 'site-packages' / 'PySide6'
fixed_binaries = []
for name, source, kind in a.binaries:
    base = Path(name).name.lower()
    if (base in ('ucrtbase.dll', 'icuuc.dll', 'icuin.dll')
            or base.startswith(('api-ms-win-', 'ext-ms-win-'))):
        continue
    if base in ('vcruntime140.dll', 'vcruntime140_1.dll'):
        candidate = qt_dir / Path(name).name
        if candidate.is_file():
            source = str(candidate)
    fixed_binaries.append((name, source, kind))
a.binaries = fixed_binaries
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='心光',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'app.ico'),
    version=str(root / 'version_info.txt'),
)
