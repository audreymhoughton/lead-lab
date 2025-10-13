# utils/normalize.py
import re
import unicodedata

# Common legal suffixes to drop from the tail
_SUFFIXES = {
    "inc","inc.","llc","l.l.c.","co","co.","company","corp","corp.","corporation",
    "ltd","ltd.","plc","gmbh","sa","s.a.","bv","b.v."
}

def normalize_company(name: str) -> str:
    s = unicodedata.normalize("NFKD", (name or "")).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)          # strip punctuation
    tokens = [t for t in s.split() if t not in {"the"}]
    # drop trailing legal suffixes
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return " ".join(tokens)

def company_key(name: str) -> str:
    n = normalize_company(name)
    return re.sub(r"\s+", "-", n).strip("-")     # slug-like key
