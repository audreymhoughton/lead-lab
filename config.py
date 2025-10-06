from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass(frozen=True)
class Settings:
    spreadsheet_id: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    worksheet_name: str = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Leads")
    sa_json_path: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./service_account.json")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    local_csv: str = os.getenv("LOCAL_CSV", "data/leads.csv")
    sheets_backend: str = os.getenv("SHEETS_BACKEND", "MOCK").upper()  # SHEETS or MOCK

settings = Settings()