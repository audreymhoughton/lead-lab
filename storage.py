# ──────────────────────────────────────────────────────────────────────────────
# File: storage.py
# -----------------------------------------------------------------------------
import os
from typing import List, Dict
from datetime import date
import pandas as pd

from config import settings
from utils.validation import validate_row
from utils.dedupe import compute_key
from utils.logging_utils import log

COLUMNS = [
    "Company", "Website", "ContactName", "Role", "Email", "Category",
    "WhyFit", "SourceURL", "Notes", "Status", "DateAdded", "Key"
]

# Ensure data directory exists
os.makedirs("data", exist_ok=True)


def init_store():
    """Create the canonical CSV with headers if it doesn't exist."""
    if not os.path.exists(settings.local_csv):
        pd.DataFrame(columns=COLUMNS).to_csv(settings.local_csv, index=False)
        log.info(f"Initialized {settings.local_csv}")
    else:
        log.info(f"Store already exists: {settings.local_csv}")


def load_df() -> pd.DataFrame:
    """Load the canonical CSV, ensuring required columns exist."""
    if not os.path.exists(settings.local_csv):
        init_store()
    df = pd.read_csv(settings.local_csv, dtype=str).fillna("")
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS]


def save_df(df: pd.DataFrame):
    """Persist the dataframe back to the canonical CSV."""
    df[COLUMNS].to_csv(settings.local_csv, index=False)
    log.info(f"Saved {len(df)} rows to {settings.local_csv}")


def upsert_row(df: pd.DataFrame, row: Dict) -> pd.DataFrame:
    """Insert new row or update existing one by Key."""
    key = row.get("Key", "")
    if not key:
        key = compute_key(row)
        row["Key"] = key
    mask = (df["Key"] == key)
    if mask.any():
        # Update existing
        for k, v in row.items():
            if k in df.columns:
                df.loc[mask, k] = v
        log.info(f"Updated: {row.get('Company', '(unknown)')} ({key})")
    else:
        # Insert new
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        log.info(f"Inserted: {row.get('Company', '(unknown)')} ({key})")
    return df


def add_rows(rows: List[Dict]):
    """Validate, stamp, dedupe and upsert a list of rows."""
    df = load_df()
    inserted = 0
    updated = 0
    for raw in rows:
        ok, msg = validate_row(raw)
        if not ok:
            log.warning(f"Skipping invalid row: {msg} — {raw}")
            continue
        if not raw.get("DateAdded"):
            raw["DateAdded"] = date.today().isoformat()
        # Ensure Key exists before upsert
        if not raw.get("Key"):
            raw["Key"] = compute_key(raw)
        before_len = len(df)
        df = upsert_row(df, raw)
        if len(df) > before_len:
            inserted += 1
        else:
            updated += 1
    save_df(df)
    log.info(f"Add complete — inserted: {inserted}, updated: {updated}")
