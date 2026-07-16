from pathlib import Path
import pandas as pd

from .paths import DAILY_PRICE_DIR, ensure_directories
from .dates import filename_to_date

def save_csv(table_data, path):
    ensure_directories()

    df = pd.DataFrame(table_data)

    df.to_csv(path, header=False, index=False)

def list_csv_files():
    ensure_directories()

    return sorted(
        [
            f.name
            for f in DAILY_PRICE_DIR.glob("*.csv")
        ]
    )

def existing_dates():
    dates = set()

    for file in DAILY_PRICE_DIR.glob("*.csv"):
        d = filename_to_date(file.name)

        if d:
            dates.add(d)

    return dates

def rows_without_serial(rows):
    return [
        tuple(str(c) for c in row[1:])
        for row in rows
    ]

def is_duplicate_of_latest(table_data, skip_file=None):
    files = list_csv_files()

    if skip_file:
        files = [
            f
            for f in files
            if f != skip_file
        ]

    if not files:
        return False

    latest = DAILY_PRICE_DIR / files[-1]

    try:
        prev = pd.read_csv(
            latest,
            header=None,
            dtype=str,
            keep_default_na=False,
        ).values.tolist()
    except Exception:
        return False

    return (
        rows_without_serial(
            table_data[1:]
        )
        ==
        rows_without_serial(
            prev[1:]
        )
    )


def save_overview_dict(data: dict, directory: Path, filename: str):
    """Save a flat dict (e.g. market summary) as a two-column label,value CSV."""
    ensure_directories()

    df = pd.DataFrame(
        list(data.items()),
        columns=["label", "value"],
    )

    df.to_csv(directory / filename, index=False)


def save_overview_table(rows: list[dict], directory: Path, filename: str):
    """Save a list of row dicts (e.g. top gainers, indices) as a CSV with
    a proper header row. Writes an empty file with no rows if `rows` is
    empty, so downstream code can always expect the file to exist."""
    ensure_directories()

    df = pd.DataFrame(rows)

    df.to_csv(directory / filename, index=False)