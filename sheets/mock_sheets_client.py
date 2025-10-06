import os
import csv
from typing import List, Dict
from config import settings               # ← absolute
from utils.logging_utils import log       # ← absolute


class SheetsClient:
    """Mock client that writes to data/exports/latest_export.csv instead of Google Sheets."""
    def __init__(self):
        os.makedirs("data/exports", exist_ok=True)
        self.export_path = "data/exports/latest_export.csv"

    # Compatibility no-ops for setup commands
    def setup_schema(self):
        log.info("MOCK backend: setup_schema() no-op")

    def ensure_buckets_tab(self):
        log.info("MOCK backend: ensure_buckets_tab() no-op")

    def upsert_rows(self, rows: List[Dict], key_col: str = "Key"):
        if not rows:
            log.info("MOCK export: no rows to write.")
            return
        # Build header from union of keys
        header = []
        for r in rows:
            for k in r.keys():
                if k not in header:
                    header.append(k)
        with open(self.export_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in header})
        log.info(f"MOCK export wrote {len(rows)} rows → {self.export_path}")