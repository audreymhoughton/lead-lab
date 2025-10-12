# enrich/contact_enrich.py
# -----------------------------------------------------------------------------
import re
import time
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from utils.logging_utils import log

UA = {"User-Agent": "LeadLab/0.2 (research-only; public contact discovery)"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Pages worth checking on most sites
PAGES = [
    "/", "/contact", "/about", "/team", "/advertise", "/sponsor", "/sponsorship",
    "/partners", "/press", "/media-kit", "/marketing", "/brand", "/partnerships"
]

# Score by local-part tokens (higher = better)
RANK = {
    "partnership": 100, "sponsor": 95, "advert": 90, "marketing": 80,
    "brand": 75, "media": 70, "press": 65, "pr": 60, "info": 40,
    "hello": 40, "contact": 35, "support": 20, "noreply": -100,
}

def _domain(url: str) -> str:
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""

def _score(email: str, site_domain: str) -> int:
    local, _, dom = email.lower().partition("@")
    score = 0
    for k, v in RANK.items():
        if k in local:
            score += v
    if dom.endswith(site_domain):
        score += 25
    return score

def _fetch(url: str, timeout: int = 8) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.ok:
            return r.text
    except Exception as e:
        log.debug(f"fetch fail {url}: {e}")
    return ""

def _harvest_from_html(html: str) -> set:
    emails = set(EMAIL_RE.findall(html or ""))
    soup = BeautifulSoup(html or "", "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?", 1)[0]
            if EMAIL_RE.match(addr):
                emails.add(addr)
    return emails

def find_contacts_for_site(website: str, delay: float = 0.5) -> dict:
    """Return dict with keys: emails (dict[email->score]) and forms (list of URLs)."""
    out = {}
    forms = []
    if not website:
        return {"emails": out, "forms": forms}
    base = website if website.startswith("http") else ("https://" + website)
    site_dom = _domain(base)
    seen = set()
    for p in PAGES:
        url = urljoin(base.rstrip("/"), p)
        if url in seen:
            continue
        seen.add(url)
        html = _fetch(url)
        if not html:
            continue
        emails = _harvest_from_html(html)
        for e in emails:
            out[e] = max(out.get(e, 0), _score(e, site_dom))
        # crude contact-form detection
        if ("<form" in html and ("contact" in url or "support" in url)) or 'type="email"' in html:
            forms.append(url)
        time.sleep(delay)
    return {"emails": out, "forms": forms}

def enrich_contacts_for_df(df, limit: int = 50, delay: float = 0.5, only_blank: bool = True):
    """
    Fill Email (and annotate Notes) for up to `limit` rows.
    - Picks the highest-scoring email.
    - Appends AltEmails and Forms to `Notes`.
    Returns a list of updated row dicts.
    """
    updates = []
    processed = 0
    for _, r in df.iterrows():
        if limit and processed >= limit:
            break
        website = str(r.get("Website", "")).strip()
        email = str(r.get("Email", "")).strip()
        if not website:
            continue
        if only_blank and email:
            continue

        res = find_contacts_for_site(website, delay=delay)
        if not res["emails"] and not res["forms"]:
            processed += 1
            continue

        best = None
        if res["emails"]:
            best = sorted(res["emails"].items(), key=lambda kv: kv[1], reverse=True)[0][0]

        notes = str(r.get("Notes", ""))
        extra = []
        if best and best.lower() != email.lower():
            r["Email"] = best
            extra.append(f"FoundEmail:{best}")

        others = [e for e in sorted(res["emails"].keys()) if (best is None or e != best)]
        if others:
            extra.append("AltEmails:" + ",".join(others[:4]))
        if res["forms"]:
            extra.append("Forms:" + ",".join(res["forms"][:3]))

        if extra:
            r["Notes"] = (notes + " | " + " ".join(extra)).strip(" | ")
            updates.append(r.to_dict())

        processed += 1
    return updates
