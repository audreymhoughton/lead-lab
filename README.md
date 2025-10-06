# lead-lab — Research-only lead generation for sponsorships

## What this does
- Lets you **add, validate, and dedupe** lead rows locally (CSV)
- Optionally **enrich** with site title/meta for context
- **Exports** to a shared **Google Sheet** as the deliverable
- Logs everything, and keeps a CSV trail for auditability

## Lead schema (columns)
- `Company` (str, required)
- `Website` (str, URL)
- `ContactName` (str)
- `Role` (str)
- `Email` (str)
- `Category` (enum: Podcast|Zine|Network|Event|Other)
- `WhyFit` (str, short rationale)
- `SourceURL` (str, where you found it)
- `Notes` (str)
- `Status` (enum: New|Reviewed|ContactedByClient|DeclinedByClient) — *client-maintained*
- `DateAdded` (ISO date)
- `Key` (internal stable dedupe key, hidden in Sheets filter if desired)

## Commands
- `python -m app init` — create `data/leads.csv` with headers if missing
- `python -m app setup-sheets` — create schema, dropdowns, and Buckets tab
- `python -m app add` — interactive prompt to add a single lead
- `python -m app import <csvpath>` — bulk import a CSV with the same columns
- `python -m app enrich` — try to fetch basic metadata for rows missing context
- `python -m app export` — push all rows to Google Sheets (upsert by `Key`)

## Backends
- `SHEETS_BACKEND=SHEETS` → real Google Sheets (requires service account + ID)
- `SHEETS_BACKEND=MOCK` → **no external calls**; writes a CSV export at `data/exports/latest_export.csv` (safe for public repos)

## Google Sheets setup
1. Create a Google Service Account in Google Cloud → download JSON key.
2. Share your target Google **Spreadsheet** with the service account email.
3. Put the JSON path in `.env` as `GOOGLE_SERVICE_ACCOUNT_JSON`.
4. Put the **Spreadsheet ID** in `.env` (from the sheet URL).

## Open-sourcing safely (no client info)
- **Never commit secrets.** Add your service account JSON to `.gitignore` and keep `.env` local.
- Use `SHEETS_BACKEND=MOCK` in `.env.example` so the default public behavior has no secrets.
- Provide redacted sample rows only in `data/leads_seed.csv` (no real emails).
- Turn on secret scanning:
  - Local pre-commit: `gitleaks` or `git-secrets`
  - GitHub → Settings → Code security → enable secret scanning & push protection
- If a secret ever leaks: revoke/rotate the key, create a new service account, and update `.env`.

## Optional Web Form (Streamlit)
Run a simple local UI for adding leads without editing CSVs:
```
pip install -r requirements.txt
streamlit run app_web/streamlit_app.py
```
- Validates fields, dedupes, saves to local CSV
- Optional toggle to also export to Google Sheets (respects `SHEETS_BACKEND`)

---