# enrich/contact_enrich.py
# -----------------------------------------------------------------------------
# Public-contact enrichment for leads.
# - Visits a focused, configurable set of pages per site
# - Extracts visible emails + mailto: links (handles common obfuscations)
# - Scores emails by local-part keywords and same-domain bonus
# - Writes best email to `Email`, keeps alternates and forms in `Notes`
# - Writes a primary contact form URL to `ContactFormURL` (if present)
# -----------------------------------------------------------------------------

import os
import re
import time
import html as _html
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Set

import requests
from bs4 import BeautifulSoup

from utils.logging_utils import log

DEFAULT_PAGES = (
    "/,/contact,/advertise,/advertising,/sponsor,/sponsorship,"
    "/partners,/brand,/brand-partnerships,/brand-partners,"
    "/media-kit,/media,/press,/marketing,/work-with-us"
)
PAGES: List[str] = os.getenv("LEADLAB_CONTACT_PAGES", DEFAULT_PAGES).split(",")
HTTP_TIMEOUT: float = float(os.getenv("LEADLAB_HTTP_TIMEOUT", "5"))

UA = {"User-Agent": "LeadLab/0.4 (research-only; public contact discovery)"}
_SESSION = requests.Session()
_SESSION.headers.update(UA)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

RANK: Dict[str, int] = {
    "partnership": 100, "sponsor": 95, "advert": 90, "marketing": 80,
    "brand": 75, "media": 70, "press": 65, "pr": 60, "podcast": 55,
    "audio": 50, "info": 40, "hello": 40, "contact": 35, "support": 20,
    "noreply": -100,
}

BRAND_INBOX_HINTS: Set[str] = {
    "partnership", "partnerships", "sponsor", "sponsors",
    "sponsorship", "sponsorships", "advert", "advertise",
    "advertising", "ads", "media", "mediarelations", "press",
    "pr", "marketing", "brand", "brandpartners", "podcast", "audio",
}

_CACHE: Dict[str, Dict[str, object]] = {}


def _domain(url: str) -> str:
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""


def _normalize_base(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def _deobfuscate_html(text: str) -> str:
    if not text:
        return ""
    s = _html.unescape(text)
    s = re.sub(r"\[\s*at\s*\]|\(\s*at\s*\)", "@", s, flags=re.I)
    s = re.sub(r"\[\s*dot\s*\]|\(\s*dot\s*\)", ".", s, flags=re.I)
    s = re.sub(r"\s+at\s+", "@", s, flags=re.I)
    s = re.sub(r"\s+dot\s+", ".", s, flags=re.I)
    return s


def _score(email: str, site_domain: str) -> int:
    local, _, dom = email.lower().partition("@")
    score = 0
    for k, v in RANK.items():
        if k in local:
            score += v
    if site_domain and dom.endswith(site_domain):
        score += 25
    if local in BRAND_INBOX_HINTS:
        score += 40
    return score


def _fetch(url: str, timeout: float = None) -> str:
    try:
        r = _SESSION.get(url, timeout=(timeout or HTTP_TIMEOUT))
        if r.ok:
            return r.text
    except Exception as e:
        log.debug(f"fetch fail {url}: {e}")
    return ""


def _harvest_from_html(html: str) -> Set[str]:
    html2 = _deobfuscate_html(html or "")
    emails = set(EMAIL_RE.findall(html2))
    soup = BeautifulSoup(html2 or "", "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?", 1)[0]
            if EMAIL_RE.match(addr):
                emails.add(addr)
    return emails


def find_contacts_for_site(website: str, delay: float = 0.3) -> Dict[str, object]:
    out: Dict[str, int] = {}
    forms: List[str] = []

    if not website:
        return {"emails": out, "forms": forms}

    base = _normalize_base(website)
    site_dom = _domain(base)
    if not site_dom:
        return {"emails": out, "forms": forms}

    if site_dom in _CACHE:
        log.debug(f"[cache] {site_dom}")
        return _CACHE[site_dom]  # type: ignore[return-value]

    log.info(f"[scan] {site_dom} — pages:{len(PAGES)}")
    seen = set()
    for p in PAGES:
        url = urljoin(base.rstrip("/"), p.strip())
        if url in seen:
            continue
        seen.add(url)

        html = _fetch(url)
        if not html:
            log.debug(f"[miss] {url}")
            continue
        log.debug(f"[ok] {url}")

        for e in _harvest_from_html(html):
            out[e] = max(out.get(e, 0), _score(e, site_dom))

        if ('<form' in html and ("contact" in url or "support" in url)) or 'type="email"' in html:
            forms.append(url)

        time.sleep(max(0.0, float(delay)))

    result: Dict[str, object] = {"emails": out, "forms": forms}
    log.info(f"[found] {site_dom} emails:{len(out)} forms:{len(forms)}")
    _CACHE[site_dom] = result
    return result


def enrich_contacts_for_df(df, limit: int = 50, delay: float = 0.3, only_blank: bool = True):
    updates: List[Dict] = []
    processed = 0

    for _, r in df.iterrows():
        if limit and processed >= limit:
            break

        website = str(r.get("Website", "")).strip()
        email = str(r.get("Email", "")).strip()

        if not website:
            continue

        res = find_contacts_for_site(website, delay=delay)
        emails: Dict[str, int] = res.get("emails", {})  # type: ignore[assignment]
        forms: List[str] = res.get("forms", [])         # type: ignore[assignment]

        # Set primary ContactFormURL if found and empty
        if forms and not str(r.get("ContactFormURL", "")).strip():
            forms_sorted = sorted(
                forms,
                key=lambda u: (
                    0 if ("advert" in u.lower() or "sponsor" in u.lower()) else
                    1 if any(k in u.lower() for k in ("brand", "media", "press")) else
                    2 if "contact" in u.lower() else
                    3
                )
            )
            r["ContactFormURL"] = forms_sorted[0]

        if not emails and not forms:
            processed += 1
            continue

        best = max(emails.items(), key=lambda kv: kv[1])[0] if emails else None

        notes = str(r.get("Notes", ""))
        extras: List[str] = []

        if best and (not only_blank or not email or best.lower() != email.lower()):
            r["Email"] = best
            extras.append(f"FoundEmail:{best}")

        others = [e for e in sorted(emails.keys()) if (not best or e != best)]
        if others:
            extras.append("AltEmails:" + ",".join(others[:4]))
        if forms:
            extras.append("Forms:" + ",".join(forms[:3]))

        if extras or r.get("ContactFormURL", ""):
            r["Notes"] = (notes + " | " + " ".join(extras)).strip(" | ")
            updates.append(r.to_dict())

        processed += 1

    return updates
