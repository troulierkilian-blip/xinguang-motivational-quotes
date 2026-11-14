import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .paths import resource_path


@dataclass(frozen=True)
class Quote:
    id: str
    text: str
    theme: str


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    english: str
    backgrounds: tuple[Path, ...]


class Catalog:
    def __init__(self, root: Path | None = None):
        root = root or resource_path("")
        data = json.loads((root / "quotes.json").read_text(encoding="utf-8"))
        themes = json.loads((root / "themes.json").read_text(encoding="utf-8"))
        self.quotes = tuple(Quote(**q) for q in data)
        self.by_id = {q.id: q for q in self.quotes}
        self.themes = {
            t["id"]: Theme(t["id"], t["name"], t["english"],
                            tuple(root / "backgrounds" / f for f in t["backgrounds"]))
            for t in themes
        }
        self.validate()

    def validate(self):
        if len(self.quotes) != 180 or len(self.by_id) != 180:
            raise ValueError("语录库必须包含 180 个唯一 ID。")
        if len({q.text.strip() for q in self.quotes}) != 180:
            raise ValueError("语录内容重复。")
        if len(self.themes) != 6:
            raise ValueError("必须包含六个主题。")
        counts = Counter(q.theme for q in self.quotes)
        if set(counts) != set(self.themes) or any(v != 30 for v in counts.values()):
            raise ValueError("每个主题必须有 30 条语录。")
        for q in self.quotes:
            if not q.text.strip():
                raise ValueError("语录不能为空。")
        for t in self.themes.values():
            if len(t.backgrounds) < 2 or len(set(t.backgrounds)) != len(t.backgrounds):
                raise ValueError("每个主题至少需要两张不同的背景。")

    def validate_files(self):
        for t in self.themes.values():
            for p in t.backgrounds:
                if not p.is_file():
                    raise FileNotFoundError(f"背景素材缺失：{p.name}")
