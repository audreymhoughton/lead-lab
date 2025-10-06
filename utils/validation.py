# ──────────────────────────────────────────────────────────────────────────────
# File: utils/validation.py
# -----------------------------------------------------------------------------
from typing import Dict, Tuple
from models import VALID_CATEGORIES, EMAIL_RE

REQUIRED = ["Company"]


def validate_row(row: Dict) -> Tuple[bool, str]:
    """Lightweight validation for a lead row.

    - Company is required
    - Category must be one of VALID_CATEGORIES (if provided)
    - Email, if present, must be a basic valid format
    """
    # Company
    company = str(row.get("Company", "")).strip()
    if not company:
        return False, "Missing required field: Company"

    # Category
    cat = str(row.get("Category", "")).strip()
    if cat and cat not in VALID_CATEGORIES:
        return False, f"Invalid Category: {cat}"

    # Email
    email = str(row.get("Email", "")).strip()
    if email and not EMAIL_RE.match(email):
        return False, f"Invalid Email format: {email}"

    return True, "OK"
