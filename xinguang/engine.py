import random
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog, Quote


@dataclass(frozen=True)
class Scene:
    quote: Quote
    background: Path


class QuoteEngine:
    """Shuffle bag: no repeats within a round or across its boundary."""

    def __init__(self, catalog: Catalog, rng: random.Random | None = None):
        self.catalog = catalog
        self.rng = rng or random.Random()
        self._bag: list[Quote] = []
        self._last_quote_id: str | None = None
        self._last_background: Path | None = None

    def next(self) -> Scene:
        if not self._bag:
            self._bag = list(self.catalog.quotes)
            self.rng.shuffle(self._bag)
            if self._bag[-1].id == self._last_quote_id:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        quote = self._bag.pop()
        candidates = [p for p in self.catalog.themes[quote.theme].backgrounds
                      if p != self._last_background]
        background = self.rng.choice(candidates)
        self._last_quote_id = quote.id
        self._last_background = background
        return Scene(quote, background)
