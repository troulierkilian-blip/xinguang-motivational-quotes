"""Diagnose missing PE imports using the actual DLLs inside the EXE."""
import os
from pathlib import Path

import pefile
from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parent.parent
reader = CArchiveReader(str(root / "dist" / "心光.exe"))
binary_names = [name for name in reader.toc if name.lower().endswith((".pyd", ".dll"))]
by_base = {}
for name in binary_names:
    by_base.setdefault(name.replace("\\", "/").split("/")[-1].lower(), []).append(name)

cache = {}


def load(name):
    if name not in cache:
        binary = pefile.PE(data=reader.extract(name), fast_load=False, max_symbol_exports=65536)
        exports = {}
        if hasattr(binary, "DIRECTORY_ENTRY_EXPORT"):
            for item in binary.DIRECTORY_ENTRY_EXPORT.symbols:
                exports[item.name] = item.forwarder
        cache[name] = binary, exports
    return cache[name]


for name in binary_names:
    binary, _ = load(name)
    for module in getattr(binary, "DIRECTORY_ENTRY_IMPORT", []):
        module_name = module.dll.decode().lower()
        matches = by_base.get(module_name, [])
        if not matches:
            continue
        for candidate in matches:
            _, exports = load(candidate)
            missing = [item.name.decode() for item in module.imports
                       if item.name is not None and item.name not in exports]
            if missing:
                print(name, "->", candidate, "MISSING:", len(missing), missing[:5])
print("Checked", len(binary_names), "bundled native modules")
