# models.py
# -----------------------------------------------------------------------------
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional, Dict, Any
import re

# Public enums / constants used across the project
VALID_CATEGORIES = {"Podcast", "Zine", "Network", "Event", "Other"}
VALID_STATUSES   = {"New", "Reviewed", "ContactedByClient", "DeclinedByClient"}

# Basic email sanity check (not exhaustive)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@dataclass
class Lead:
    """
    Canonical Lead schema for Lead Lab.

    This represents a *research-only* sponsorship lead. It intentionally excludes
    any outreach/BD fields. The `Key` is a stable, deterministic hash computed
    elsewhere (see utils/dedupe.py) from (Company|Website|Email).
    """

    Company: str
    Website: Optional[str] = ""
    ContactName: Optional[str] = ""
    Role: Optional[str] = ""
    Email: Optional[str] = ""
    Category: Optional[str] = "Other"   # Podcast|Zine|Network|Event|Other
    WhyFit: Optional[str] = ""
    SourceURL: Optional[str] = ""
    Notes: Optional[str] = ""
    Status: Optional[str] = "New"       # Client-maintained downstream
    DateAdded: Optional[str] = date.today().isoformat()
    Key: Optional[str] = ""             # Deterministic dedupe key

    def to_row(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Lead":
        """Create a Lead with sensible defaults and light normalization."""
        norm = {k: ("" if v is None else str(v)) for k, v in dict(data).items()}

        if not norm.get("Company"):
            raise ValueError("Company is required")

        cat = norm.get("Category", "Other") or "Other"
        if cat not in VALID_CATEGORIES:
            cat = "Other"

        status = norm.get("Status", "New") or "New"
        if status not in VALID_STATUSES:
            status = "New"

        d = norm.get("DateAdded") or date.today().isoformat()

        return Lead(
            Company=norm.get("Company", "").strip(),
            Website=norm.get("Website", "").strip(),
            ContactName=norm.get("ContactName", "").strip(),
            Role=norm.get("Role", "").strip(),
            Email=norm.get("Email", "").strip(),
            Category=cat,
            WhyFit=norm.get("WhyFit", "").strip(),
            SourceURL=norm.get("SourceURL", "").strip(),
            Notes=norm.get("Notes", "").strip(),
            Status=status,
            DateAdded=d,
            Key=norm.get("Key", "").strip(),
        )
