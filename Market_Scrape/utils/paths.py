from pathlib import Path
from datetime import date

ROOT_DIR = Path("Data")
CSV_DIR = ROOT_DIR / "csv"
DAILY_PRICE_DIR = CSV_DIR / "daily_price"
OVERVIEW_DIR = CSV_DIR / "overview"


def ensure_directories():
    DAILY_PRICE_DIR.mkdir(parents=True, exist_ok=True)
    OVERVIEW_DIR.mkdir(parents=True, exist_ok=True)


def overview_dir_for_date(d: date) -> Path:
    """Data/csv/overview/YYYY-MM-DD/ — created on demand."""
    path = OVERVIEW_DIR / d.isoformat()
    path.mkdir(parents=True, exist_ok=True)

    return path