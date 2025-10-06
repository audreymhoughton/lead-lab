# finders/finder.py
from typing import List, Dict, Set
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from utils.logging_utils import log

USER_AGENT = "LeadLab/0.1 (+research-only; no outreach)"
BLOCKED_DOMAINS: Set[str] = {
    "facebook.com","x.com","twitter.com","instagram.com","youtube.com",
    "tiktok.com","linkedin.com","pinterest.com","itunes.apple.com",
}

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def _looks_external(href: str, source_domain: str) -> bool:
    d = _domain(href)
    return d and d != source_domain and d not in BLOCKED_DOMAINS

def _clean_name(text: str) -> str:
    t = (text or "").strip()
    return re.sub(r"\s+", " ", t)[:80]

def extract_candidates_from_html(html: str, source_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    src_dom = _domain(source_url)
    rows: List[Dict] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = _clean_name(a.get_text(" "))
        if not text or len(text) < 2:    continue
        if not href.startswith("http"):  continue
        if not _looks_external(href, src_dom):  continue
        rows.append({
            "Company": text,
            "Website": href,
            "WhyFit": f"Mentioned in sponsor/brands list on {src_dom}",
            "SourceURL": source_url,
        })
    return rows

def extract_candidates_from_url(url: str) -> List[Dict]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
        resp.raise_for_status()
        return extract_candidates_from_html(resp.text, url)
    except Exception as e:
        log.warning(f"finder: failed {url} — {e}")
        return []

def find_from_urls(urls: List[str], topic: str = "podcast") -> List[Dict]:
    """Parse list/article URLs and return candidate lead rows. Review results."""
    out: List[Dict] = []
    for url in urls:
        cand = extract_candidates_from_url(url)
        for r in cand:
            r.setdefault("Category", "Podcast" if topic=="podcast" else ("Network" if topic=="network" else "Event"))
            r.setdefault("ContactName",""); r.setdefault("Role",""); r.setdefault("Email","")
            r.setdefault("Notes",""); r.setdefault("Status","New")
        out.extend(cand)
    return out
