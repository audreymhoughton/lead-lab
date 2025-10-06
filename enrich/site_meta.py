# enrich/site_meta.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from utils.logging_utils import log   # ← changed: no leading dots

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LeadLabBot/1.0; +https://github.com/yourusername/lead-lab)"
    )
}

def fetch_site_meta(url: str, timeout: int = 5) -> dict:
    meta = {"MetaTitle": "", "MetaDescription": "", "Domain": ""}
    if not url or not url.startswith(("http://", "https://")):
        return meta

    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if not r.ok:
            log.warning(f"fetch_site_meta: HTTP {r.status_code} for {url}")
            return meta

        soup = BeautifulSoup(r.text, "html.parser")
        title_tag = soup.find("title")
        desc_tag = soup.find("meta", attrs={"name": "description"})

        meta["MetaTitle"] = (title_tag.text.strip() if title_tag else "")[:200]
        meta["MetaDescription"] = (
            desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
        )[:300]
        meta["Domain"] = urlparse(url).netloc

        return meta
    except Exception as e:
        log.warning(f"fetch_site_meta: failed for {url} ({e})")
        return meta
