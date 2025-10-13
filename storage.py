# storage.py
# -----------------------------------------------------------------------------
import os
from typing import List, Dict
from datetime import date
import pandas as pd
from pandas.errors import EmptyDataError

from config import settings
from utils.validation import validate_row
from utils.dedupe import compute_key
from utils.logging_utils import log
from utils.normalize import company_key  # requires utils/normalize.py

# Canonical schema (removed ContactName, Role)
COLUMNS = [
    "Company", "CompanyKey", "Website", "Email", "ContactFormURL",
    "Category", "WhyFit", "SourceURL", "Notes", "Status", "DateAdded", "Key"
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


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all required columns exist and backfill computed ones."""
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    # Backfill CompanyKey where missing
    if "CompanyKey" in df.columns and "Company" in df.columns:
        mask_ck = (df["Company"].astype(str) != "") & (df["CompanyKey"].astype(str) == "")
        if mask_ck.any():
            df.loc[mask_ck, "CompanyKey"] = df.loc[mask_ck, "Company"].apply(company_key)
    # Return only canonical columns (drops deprecated ContactName/Role if present)
    return df[COLUMNS]


def load_df() -> pd.DataFrame:
    """Load the canonical CSV, ensuring required columns exist (auto-repair empties)."""
    if not os.path.exists(settings.local_csv):
        init_store()
    try:
        df = pd.read_csv(settings.local_csv, dtype=str).fillna("")
    except EmptyDataError:
        # File exists but has no header/rows: recreate with headers
        pd.DataFrame(columns=COLUMNS).to_csv(settings.local_csv, index=False)
        df = pd.DataFrame(columns=COLUMNS)
    return _ensure_columns(df)


def save_df(df: pd.DataFrame):
    """Persist the dataframe back to the canonical CSV."""
    _ensure_columns(df).to_csv(settings.local_csv, index=False)
    log.info(f"Saved {len(df)} rows to {settings.local_csv}")


def upsert_row(df: pd.DataFrame, row: Dict) -> pd.DataFrame:
    """
    Insert new row or update existing one.
    Priority merge keys:
      1) Key (stable hash of Company|Website|Email)
      2) CompanyKey (normalized company name) to prevent duplicates by company
    """
    # Compute keys for the incoming row
    row["CompanyKey"] = row.get("CompanyKey") or company_key(row.get("Company", ""))
    row["Key"] = row.get("Key") or compute_key(row)

    key = row["Key"]
    ck = row["CompanyKey"]

    mask_key = (df["Key"] == key) if key else pd.Series(False, index=df.index)
    mask_co = (df["CompanyKey"] == ck) if ck else pd.Series(False, index=df.index)

    if mask_key.any() or mask_co.any():
        idx = df.index[mask_key | mask_co]
        i0 = idx[0]  # update the first match
        for k, v in row.items():
            if k in df.columns and str(v) != "":
                df.at[i0, k] = v
        # If multiple duplicates exist for the same company, collapse them
        if len(idx) > 1:
            df = df.drop(index=idx[1:])
        log.info(f"Upsert merge → {row.get('Company','(unknown)')} [{ck}]")
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        log.info(f"Inserted: {row.get('Company','(unknown)')} ({ck})")

    return df


def add_rows(rows: List[Dict]):
    """Validate, stamp, compute keys, dedupe/merge, and persist a list of rows."""
    df = load_df()
    inserted = 0
    updated = 0

    for raw in rows:
        ok, msg = validate_row(raw)
        if not ok:
            log.warning(f"Skipping invalid row: {msg} — {raw}")
            continue

        # Defaults
        if not raw.get("DateAdded"):
            raw["DateAdded"] = date.today().isoformat()

        # Ensure keys exist for dedupe/merge
        raw["CompanyKey"] = raw.get("CompanyKey") or company_key(raw.get("Company", ""))
        raw["Key"] = raw.get("Key") or compute_key(raw)

        before = len(df)
        df = upsert_row(df, raw)
        if len(df) > before:
            inserted += 1
        else:
            updated += 1

    save_df(df)
    log.info(f"Add complete — inserted: {inserted}, updated: {updated}")
