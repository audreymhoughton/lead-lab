# ──────────────────────────────────────────────────────────────────────────────
# File: utils/dedupe.py
# -----------------------------------------------------------------------------
import hashlib
from typing import Dict

# Deterministic key based on stable identifying fields
KEY_FIELDS = ["Company", "Website", "Email"]


def compute_key(row: Dict) -> str:
    """Compute a short deterministic hash key for a lead row.

    Uses the lowercased and trimmed values of Company, Website, and Email.
    Returns the first 16 characters of a SHA1 hash, sufficient for uniqueness
    in small datasets.
    """
    base = "|".join((str(row.get(k, "")).strip().lower() for k in KEY_FIELDS))
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
