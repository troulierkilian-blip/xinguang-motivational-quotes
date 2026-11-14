import json
import os
import shutil
import tempfile
from pathlib import Path


class FavoritesStore:
    """Atomic user-data persistence; failed writes never change in-memory state."""

    def __init__(self, path: Path, known_ids: set[str]):
        self.path = path
        self.known_ids = known_ids
        self.ids: list[str] = []
        self.warning = ""
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("收藏格式不正确")
            ids = data.get("ids")
            if not isinstance(ids, list) or any(not isinstance(q, str) for q in ids):
                raise ValueError("收藏列表不正确")
            self.ids = list(dict.fromkeys(q for q in ids if q in self.known_ids))
        except (OSError, ValueError, UnicodeError):
            try:
                backup = self.path.with_name(self.path.name + ".corrupt")
                index = 1
                while backup.exists():
                    backup = self.path.with_name(self.path.name + f".corrupt.{index}")
                    index += 1
                shutil.copy2(self.path, backup)
                self.warning = "收藏文件无法读取，已保留备份。你可以继续浏览和重新收藏。"
            except OSError:
                self.warning = "收藏文件无法读取。你可以继续浏览，保存收藏时可能需要检查目录权限。"

    def contains(self, quote_id: str) -> bool:
        return quote_id in self.ids

    def toggle(self, quote_id: str) -> bool:
        if quote_id not in self.known_ids:
            raise ValueError("未知语录 ID")
        new_ids = list(self.ids)
        added = quote_id not in new_ids
        if added:
            new_ids.insert(0, quote_id)
        else:
            new_ids.remove(quote_id)
        self._save(new_ids)
        self.ids = new_ids
        return added

    def _save(self, ids: list[str]):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=self.path.parent, suffix=".tmp",
                                             delete=False) as stream:
                temp_path = Path(stream.name)
                json.dump({"version": 1, "ids": ids}, stream,
                          ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
