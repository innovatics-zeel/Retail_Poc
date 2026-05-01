"""
ingest_raw_json.py
─────────────────────────────────────────────────────────
Read a raw JSON file and save every record to its correct table.
The category field in each record determines which table it goes to —
no hardcoded model or table names here.

Usage:
    python3 pipeline/ingest_raw_json.py                                # default path
    python3 pipeline/ingest_raw_json.py data/nordstrom_womens_dresses.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import test_connection
from pipeline.ingest import ingest_batch

DEFAULT_PATH = "data/nordstrom_womens_dresses.json"


def ingest_json_file(path: str) -> dict:
    """
    Read *path* (list or single dict), group by category,
    and call ingest_batch for each group so the registry
    routes each record to the correct table automatically.
    """
    raw_list = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw_list, dict):
        raw_list = [raw_list]

    # group by category so each batch goes to the right table
    by_category: dict[str, list] = defaultdict(list)
    for item in raw_list:
        cat = item.get("category", "")
        if cat:
            by_category[cat].append(item)
        else:
            logger.warning(f"Skipping record with no category: {item.get('url', '?')}")

    totals = {"total": len(raw_list), "success": 0, "failed": 0, "skipped": 0}
    for category, records in by_category.items():
        logger.info(f"Ingesting {len(records)} records for category: {category}")
        summary = ingest_batch(records, category)
        totals["success"] += summary["success"]
        totals["failed"]  += summary["failed"]
        totals["skipped"] += summary["skipped"]

    return totals


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    if not Path(path).exists():
        logger.error(f"File not found: {path}")
        sys.exit(1)

    if not test_connection():
        logger.error("Cannot connect to PostgreSQL — check your .env")
        sys.exit(1)

    logger.info(f"Ingesting: {path}")
    result = ingest_json_file(path)
    logger.info(f"Done — ✅ {result['success']} | ❌ {result['failed']} | ⏭ {result['skipped']} of {result['total']}")

    if result["failed"]:
        sys.exit(1)
