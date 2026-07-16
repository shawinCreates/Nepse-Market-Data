"""
One-time (or re-runnable) backfill: loads every CSV already sitting in
Data/csv/daily_price/ into Postgres. Doesn't touch the network — useful
for pushing years of already-scraped history into Neon in one go, since
market_history.py / market_missing.py deliberately skip re-fetching days
whose CSV already exists.

Usage (from the project root, same place you'd run `scrapy crawl ...`):

    python backfilldb.py
"""

import pandas as pd

from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories
from Market_Scrape.utils.dates import filename_to_date
from Market_Scrape.utils.db import ensure_schema, load_daily_price_rows


def main():
    ensure_directories()
    ensure_schema()

    files = sorted(DAILY_PRICE_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in {DAILY_PRICE_DIR}")
        return

    total_files = 0
    total_rows = 0

    for path in files:
        trade_date = filename_to_date(path.name)

        if trade_date is None:
            print(f"Skipping {path.name}: couldn't parse a date from the filename.")
            continue

        table_data = pd.read_csv(
            path, header=None, dtype=str, keep_default_na=False
        ).values.tolist()

        row_count = load_daily_price_rows(table_data, trade_date)

        total_files += 1
        total_rows += row_count

        print(f"{path.name}: upserted {row_count} rows")

    print(f"\nDone. {total_files} files processed, {total_rows} rows upserted.")


if __name__ == "__main__":
    main()