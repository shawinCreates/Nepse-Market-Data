from pathlib import Path
import pandas as pd

from .paths import CSV_DIR, ensure_directories
from .dates import filename_to_date

def save_csv(table_data, path):
    ensure_directories()

    df = pd.DataFrame(table_data)

    df.to_csv(
        path,
        header=False,
        index=False,
    )

def list_csv_files():
    ensure_directories()

    return sorted(
        [
            f.name
            for f in CSV_DIR.glob("*.csv")
        ]
    )

def existing_dates():
    dates = set()

    for file in CSV_DIR.glob("*.csv"):
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

    latest = CSV_DIR / files[-1]

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
