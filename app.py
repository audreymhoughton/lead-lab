# Absolute imports for script mode
import argparse
from datetime import date
from typing import List
import pandas as pd

from config import settings
from storage import init_store, add_rows, load_df
from utils.logging_utils import log
from enrich.site_meta import fetch_site_meta
from finders.finder import find_from_urls
from enrich.contact_enrich import enrich_contacts_for_df

# Sheets backend selection
if settings.sheets_backend == "SHEETS":
    from sheets.sheets_client import SheetsClient
else:
    from sheets.mock_sheets_client import SheetsClient


# Example row used by interactive add
EXAMPLE_ROW = {
    "Company": "Acme Brand",
    "Website": "https://example.com",
    "ContactName": "Jane Doe",
    "Role": "Marketing Director",
    "Email": "jane@example.com",
    "Category": "Podcast",
    "WhyFit": "Sponsors similar shows; strong brand alignment",
    "SourceURL": "https://example.com/sponsorships",
    "Notes": "",
    "Status": "New",
    "DateAdded": date.today().isoformat(),
}


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------
def cmd_init(_):
    init_store()


def cmd_setup_sheets(_):
    sc = SheetsClient()
    if hasattr(sc, "setup_schema"):
        sc.setup_schema()
    if hasattr(sc, "ensure_buckets_tab"):
        sc.ensure_buckets_tab()


def cmd_add(_):
    print("\nAdd a lead (press Enter to skip optional fields)\n")
    row = {}
    for k in EXAMPLE_ROW.keys():
        if k in ("Status", "DateAdded"):
            continue
        val = input(f"{k} [{EXAMPLE_ROW[k]}]: ").strip()
        row[k] = val or EXAMPLE_ROW[k]
    row["Status"] = "New"
    row["DateAdded"] = date.today().isoformat()
    add_rows([row])


def cmd_import(args):
    import_path = args.path
    df = pd.read_csv(import_path, dtype=str).fillna("")
    rows = df.to_dict(orient="records")
    add_rows(rows)


def cmd_enrich(_):
    df = load_df()
    updated = []
    for _, r in df.iterrows():
        notes = str(r.get("Notes", ""))
        website = str(r.get("Website", "")).strip()
        if website and (not notes or len(notes) < 5):
            meta = fetch_site_meta(website)
            title = meta.get("MetaTitle", "").strip()
            if title:
                r["Notes"] = (notes + f" | Title: {title}").strip(" |")
                updated.append(r.to_dict())
    if updated:
        add_rows(updated)
        log.info(f"Enriched {len(updated)} rows with site titles")
    else:
        log.info("No rows needed enrichment.")


def cmd_enrich_contacts(args):
    if enrich_contacts_for_df is None:
        log.error("Contact enrichment module not available. Add enrich/contact_enrich.py first.")
        return
    df = load_df()
    changed = enrich_contacts_for_df(
        df,
        limit=args.limit,
        delay=args.delay,
        only_blank=args.only_blank,
    )
    if changed:
        add_rows(changed)
        log.info(f"Contact enrichment updated {len(changed)} rows.")
    else:
        log.info("No contacts found.")


def cmd_find(args):
    if find_from_urls is None:
        log.error("Finder not available. Add finders/finder.py first.")
        return
    urls: List[str] = args.urls or []
    if args.urls_file:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    if not urls:
        log.error("No URLs provided. Use --urls or --urls-file.")
        return
    rows = find_from_urls(urls, topic=args.topic)
    if rows:
        add_rows(rows)
        log.info(f"Finder added/updated {len(rows)} candidate leads from {len(urls)} URL(s).")
    else:
        log.info("Finder produced no candidates. Try different sources.")


def cmd_export(_):
    df = load_df()
    rows = df.to_dict(orient="records")
    sc = SheetsClient()
    sc.upsert_rows(rows)


# -----------------------------------------------------------------------------
# Parser / Main
# -----------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="lead-lab",
        description="Research-only lead generator: local CSV → Google Sheets or mock export",
    )
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("setup-sheets").set_defaults(func=cmd_setup_sheets)
    sub.add_parser("add").set_defaults(func=cmd_add)

    pi = sub.add_parser("import")
    pi.add_argument("path")
    pi.set_defaults(func=cmd_import)

    sub.add_parser("enrich").set_defaults(func=cmd_enrich)

    # Contact enrichment
    pec = sub.add_parser("enrich-contacts")
    pec.add_argument("--limit", type=int, default=50, help="Max rows to process")
    pec.add_argument("--delay", type=float, default=0.5, help="Delay between page fetches (seconds)")
    pec.add_argument("--only-blank", action="store_true", help="Only fill rows with empty Email")
    pec.set_defaults(func=cmd_enrich_contacts)

    # Finder from list/article URLs (optional)
    pf = sub.add_parser("find")
    pf.add_argument("--urls", nargs="*", help="One or more list/article URLs to parse")
    pf.add_argument("--urls-file", help="Text file with one URL per line")
    pf.add_argument("--topic", default="podcast", choices=["podcast", "network", "event"], help="Category hint for WhyFit")
    pf.set_defaults(func=cmd_find)

    sub.add_parser("export").set_defaults(func=cmd_export)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
