import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xinguang.catalog import Catalog
from xinguang.engine import QuoteEngine
from xinguang.favorites import FavoritesStore


class CatalogAndEngineTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()

    def test_complete_catalog_and_backgrounds(self):
        self.catalog.validate_files()
        self.assertEqual(len(self.catalog.by_id), 180)
        self.assertEqual(len({q.text for q in self.catalog.quotes}), 180)
        self.assertEqual(sum(len(t.backgrounds) for t in self.catalog.themes.values()), 12)

    def test_ten_full_rounds_and_scene_matching(self):
        engine = QuoteEngine(self.catalog, random.Random(10))
        scenes = [engine.next() for _ in range(1800)]
        for start in range(0, 1800, 180):
            self.assertEqual(len({s.quote.id for s in scenes[start:start + 180]}), 180)
        for current, following in zip(scenes, scenes[1:]):
            self.assertNotEqual(current.quote.id, following.quote.id)
            self.assertNotEqual(current.background, following.background)
            self.assertIn(following.background, self.catalog.themes[following.quote.theme].backgrounds)

    def test_same_theme_always_gets_different_image(self):
        engine = QuoteEngine(self.catalog, random.Random(3))
        quotes = [q for q in self.catalog.quotes if q.theme == "hope"]
        engine._bag = quotes[:3]
        scenes = [engine.next() for _ in range(3)]
        self.assertNotEqual(scenes[0].background, scenes[1].background)
        self.assertNotEqual(scenes[1].background, scenes[2].background)

    def test_round_boundary_even_with_adversarial_shuffle(self):
        class NoShuffle(random.Random):
            def shuffle(self, values):
                pass
        engine = QuoteEngine(self.catalog, NoShuffle(4))
        first = engine.next()
        engine._bag = []
        second = engine.next()
        self.assertNotEqual(first.quote.id, second.quote.id)


class FavoritesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "用户收藏" / "favorites.json"
        self.ids = {"hope_01", "hope_02"}

    def test_add_remove_and_reopen(self):
        store = FavoritesStore(self.path, self.ids)
        self.assertTrue(store.toggle("hope_01"))
        reopened = FavoritesStore(self.path, self.ids)
        self.assertTrue(reopened.contains("hope_01"))
        self.assertFalse(reopened.toggle("hope_01"))
        self.assertFalse(FavoritesStore(self.path, self.ids).contains("hope_01"))

    def test_duplicates_and_unknown_ids_are_ignored(self):
        self.path.parent.mkdir()
        self.path.write_text(json.dumps({"version": 1, "ids": ["hope_01", "hope_01", "gone"]}), encoding="utf-8")
        self.assertEqual(FavoritesStore(self.path, self.ids).ids, ["hope_01"])

    def test_corrupt_file_is_preserved(self):
        self.path.parent.mkdir()
        self.path.write_text("broken JSON", encoding="utf-8")
        store = FavoritesStore(self.path, self.ids)
        self.assertEqual(store.ids, [])
        self.assertTrue(store.warning)
        self.assertEqual(self.path.with_name("favorites.json.corrupt").read_text(encoding="utf-8"), "broken JSON")
        store.toggle("hope_01")
        self.assertTrue(FavoritesStore(self.path, self.ids).contains("hope_01"))

    def test_failed_atomic_write_preserves_existing_state(self):
        store = FavoritesStore(self.path, self.ids)
        store.toggle("hope_01")
        with patch("xinguang.favorites.os.replace", side_effect=PermissionError("read-only")):
            with self.assertRaises(OSError):
                store.toggle("hope_02")
        self.assertEqual(store.ids, ["hope_01"])
        self.assertEqual(FavoritesStore(self.path, self.ids).ids, ["hope_01"])
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):
            FavoritesStore(self.path, self.ids).toggle("unknown")


if __name__ == "__main__":
    unittest.main()
