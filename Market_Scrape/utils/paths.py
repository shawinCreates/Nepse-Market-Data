from pathlib import Path

ROOT_DIR = Path("Data")

CSV_DIR = ROOT_DIR / "csv"
EXCEL_DIR = ROOT_DIR / "excel"

COMBINED_EXCEL = EXCEL_DIR / "combined_excel.xlsx"
CSV_LIST_FILE = EXCEL_DIR / "list_of_csv_files.txt"

def ensure_directories():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)

