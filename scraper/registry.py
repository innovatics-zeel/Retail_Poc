"""
registry.py
Auto-discovers all *_scraper.py modules in this package and builds a
(platform, category) → scraper_class lookup table.

Adding a new scraper requires NO changes here — just drop a new file that:
  1. Subclasses BaseScraper
  2. Sets PLATFORM, CATEGORY, SCHEMA_CLASS class attributes
  3. Implements to_db_values(data) -> dict
"""
import glob
import importlib
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scraper.base_scraper import BaseScraper

_registry: dict[tuple[str, str], type] = {}
_discovered = False


def _autodiscover() -> None:
    global _discovered
    if _discovered:
        return

    scraper_dir = os.path.dirname(__file__)
    for path in sorted(glob.glob(os.path.join(scraper_dir, "*_scraper.py"))):
        module_name = os.path.basename(path)[:-3]
        importlib.import_module(f"scraper.{module_name}")

    from scraper.base_scraper import BaseScraper

    def _collect(cls):
        for sub in cls.__subclasses__():
            platform = getattr(sub, "PLATFORM", "")
            category = getattr(sub, "CATEGORY", "")
            if platform and category:
                _registry[(platform.lower(), category.lower())] = sub
            _collect(sub)

    _collect(BaseScraper)
    _discovered = True


def get_scraper(platform: str, category: str) -> type:
    _autodiscover()
    key = (platform.lower(), category.lower())
    if key not in _registry:
        raise ValueError(f"No scraper registered for {platform}/{category}")
    return _registry[key]


def get_by_category(category: str) -> type:
    _autodiscover()
    cat = category.lower()
    for (_, c), cls in _registry.items():
        if c == cat:
            return cls
    raise ValueError(f"No scraper registered for category: {category}")


def all_scrapers() -> list[type]:
    _autodiscover()
    return list(_registry.values())
