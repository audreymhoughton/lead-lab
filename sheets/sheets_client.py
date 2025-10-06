# sheets/sheets_client.py
# ---------------------------------------------------------------------
# Real Google Sheets integration for lead-lab
# ---------------------------------------------------------------------
import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    set_frozen, set_column_width, cellFormat, textFormat,
    DataValidationRule, BooleanCondition, set_data_validation_for_cell_range,
)
from typing import List, Dict
from config import settings               # ← absolute
from utils.logging_utils import log       # ← absolute
import gspread.utils as gutils


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

LEAD_HEADER = [
    "Company", "Website", "ContactName", "Role", "Email",
    "Category", "WhyFit", "SourceURL", "Notes",
    "Status", "DateAdded", "Key"
]

STATUS_LIST = ["New", "Reviewed", "ContactedByClient", "DeclinedByClient"]
CATEGORY_LIST = ["Podcast", "Zine", "Network", "Event", "Other"]

class SheetsClient:
    """Google Sheets client for exporting and managing Lead Lab data."""

    def __init__(self):
        creds = Credentials.from_service_account_file(
            settings.sa_json_path, scopes=SCOPES
        )
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(settings.spreadsheet_id)
        self.ws = self._get_or_create_worksheet(settings.worksheet_name)

    # ------------------ Setup & schema management ------------------

    def _get_or_create_worksheet(self, name: str):
        try:
            return self.sh.worksheet(name)
        except gspread.WorksheetNotFound:
            log.info(f"Creating worksheet '{name}'")
            return self.sh.add_worksheet(title=name, rows=1000, cols=20)

    def setup_schema(self):
        """Ensure header, column widths, frozen rows, and dropdowns."""
        header = self.ws.row_values(1)
        if not header:
            self.ws.update([LEAD_HEADER])
        else:
            missing = [h for h in LEAD_HEADER if h not in header]
            if missing:
                header += missing
                self.ws.update([header])

        # Freeze header row
        set_frozen(self.ws, rows=1)

        # Column widths
        widths = {
            1: 220, 2: 220, 3: 160, 4: 140, 5: 220, 6: 110,
            7: 320, 8: 260, 9: 280, 10: 160, 11: 120, 12: 200,
        }
        for col, w in widths.items():
            set_column_width(self.ws, col, w)

        # Bold header row
        fmt = cellFormat(textFormat=textFormat(bold=True))
        self.ws.format("1:1", fmt)

        # Add validation lists
        try:
            vtab = self.sh.worksheet("_Validation")
        except gspread.WorksheetNotFound:
            vtab = self.sh.add_worksheet(title="_Validation", rows=10, cols=5)

        vtab.update("A1", [["Status"], *[[s] for s in STATUS_LIST]])
        vtab.update("B1", [["Category"], *[[c] for c in CATEGORY_LIST]])

        status_range = f"_Validation!A2:A{1 + len(STATUS_LIST)}"
        cat_range = f"_Validation!B2:B{1 + len(CATEGORY_LIST)}"

        header = self.ws.row_values(1)
        status_col = header.index("Status") + 1
        cat_col = header.index("Category") + 1

        self._apply_dropdown_validation(status_col, status_range)
        self._apply_dropdown_validation(cat_col, cat_range)
        log.info("Sheet schema & validations configured.")

    def _apply_dropdown_validation(self, col_idx: int, list_a1: str):
        rng = f"{gutils.rowcol_to_a1(2, col_idx)}:{gutils.rowcol_to_a1(10000, col_idx)}"
        rule = DataValidationRule(
            BooleanCondition("ONE_OF_RANGE", [list_a1]),
            showCustomUi=True,
        )
        set_data_validation_for_cell_range(self.ws, rng, rule)

    def ensure_buckets_tab(self):
        """Create/update Buckets tab with summary formulas."""
        try:
            btab = self.sh.worksheet("Buckets")
        except gspread.WorksheetNotFound:
            btab = self.sh.add_worksheet(title="Buckets", rows=100, cols=6)

        btab.update(
            "A1",
            [
                ["Counts by Category"],
                ["Category", "Count"],
                ["=UNIQUE(Leads!F2:F)", "=ARRAYFORMULA(COUNTIF(Leads!F2:F, A3:A))"],
            ],
        )

        btab.update(
            "D1",
            [
                ["Counts by Status"],
                ["Status", "Count"],
                ["=UNIQUE(Leads!J2:J)", "=ARRAYFORMULA(COUNTIF(Leads!J2:J, D3:D))"],
            ],
        )

        btab.update(
            "A8",
            [["Quick Filters — use header dropdowns on the Leads tab"]],
        )
        log.info("Buckets tab ensured with summary formulas.")

    # ------------------ Data export ------------------

    def upsert_rows(self, rows: List[Dict], key_col: str = "Key"):
        """Insert or update rows in the Google Sheet."""
        if not rows:
            log.info("No rows to export.")
            return

        header = self.ws.row_values(1)
        if not header:
            header = LEAD_HEADER
            self.ws.update([header])

        header_map = {h: i for i, h in enumerate(header)}
        existing = self.ws.get_all_records()
        index = {str(r.get(key_col, "")): i + 2 for i, r in enumerate(existing)}

        # Ensure all columns exist
        for k in LEAD_HEADER:
            if k not in header_map:
                header.append(k)
                header_map[k] = len(header_map)
        if header != self.ws.row_values(1):
            self.ws.update([header])

        # Upsert logic
        for row in rows:
            values = [row.get(h, "") for h in header]
            key = str(row.get(key_col, ""))
            if key in index:
                rownum = index[key]
                rng = gutils.rowcol_to_a1(rownum, 1) + ":" + gutils.rowcol_to_a1(
                    rownum, len(header)
                )
                self.ws.update(rng, [values], value_input_option="RAW")
            else:
                self.ws.append_rows([values], value_input_option="RAW")

        log.info(f"Exported {len(rows)} rows to Google Sheets → {settings.worksheet_name}")
