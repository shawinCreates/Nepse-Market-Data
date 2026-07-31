"""
CSV -> Postgres sync: loads every CSV already sitting in
Data/csv/daily_price/ into Postgres, filling only the dates and symbols
the database is missing. Doesn't touch the network — the CSVs are the
source of truth, exactly as with market_history.py / market_missing.py,
which deliberately skip re-fetching days whose CSV already exists.

Usage (from the project root, same place you'd run `scrapy crawl ...`):

    python backfilldb.py            # fill only what's missing in the DB
    python backfilldb.py --check    # dry run: report missing data, write nothing
    python backfilldb.py --force    # re-upsert every file (idempotent)

One malformed CSV never aborts the run: the file is reported as failed
and the rest continue.
"""

import argparse

import pandas as pd

from Market_Scrape.utils.dates import filename_to_date
from Market_Scrape.utils.db import (
    DATABASE_URL,
    bulk_upsert,
    daily_price_symbols,
    ensure_schema,
    get_connection,
    load_daily_price_rows,
)
from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories


def db_symbols_per_date():
    """trade_date -> set of symbols already present in the DB."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT trade_date, symbol FROM daily_price")

        result = {}

        for trade_date, symbol in cur.fetchall():
            result.setdefault(trade_date, set()).add(symbol)

        return result


def read_csv(path):
    return pd.read_csv(path, header=None, dtype=str, keep_default_na=False).values.tolist()


def main():
    parser = argparse.ArgumentParser(
        description="Sync Data/csv/daily_price/ CSVs into the Postgres daily_price table."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run: report what's missing from the DB without writing anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upsert every CSV, even dates/symbols already present (idempotent).",
    )
    args = parser.parse_args()

    if not DATABASE_URL:
        parser.error("DATABASE_URL is not set. Add it to .env or export it.")

    ensure_directories()
    ensure_schema()

    files = sorted(DAILY_PRICE_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in {DAILY_PRICE_DIR}")
        return

    db_map = db_symbols_per_date()

    up_to_date = []
    missing_dates = []
    partial_dates = []
    missing_rows = 0
    total_rows = 0
    failures = []

    with bulk_upsert():
        for path in files:
            trade_date = filename_to_date(path.name)

            if trade_date is None:
                failures.append(f"{path.name}: couldn't parse a date from the filename")
                continue

            try:
                table_data = read_csv(path)
                csv_symbols = daily_price_symbols(table_data)

                if not csv_symbols:
                    failures.append(f"{path.name}: no Symbol column or no data rows")
                    continue

                if args.force:
                    missing = csv_symbols
                else:
                    existing = db_map.get(trade_date, set())
                    missing = csv_symbols - existing

                if not missing:
                    up_to_date.append(path.name)
                    continue

                missing_rows += len(missing)

                if trade_date in db_map:
                    partial_dates.append(f"{path.name} ({len(missing)} symbols missing)")
                else:
                    missing_dates.append(path.name)

                if args.check:
                    continue

                row_count = load_daily_price_rows(table_data, trade_date)
                total_rows += row_count
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")

    print(f"\n{len(files)} CSV files scanned.")

    if missing_dates:
        print(f"\nDates absent from the DB ({len(missing_dates)}):")
        print("  " + ", ".join(missing_dates))

    if partial_dates:
        print(f"\nDates present but with missing symbols ({len(partial_dates)}):")
        for entry in partial_dates:
            print("  " + entry)

    if up_to_date:
        print(f"\nAlready up to date ({len(up_to_date)} files): skipped.")

    if failures:
        print(f"\nFailed ({len(failures)} files):")
        for failure in failures:
            print("  " + failure)

    if args.check:
        print(f"\nDRY RUN — would fill {missing_rows} missing rows across "
              f"{len(missing_dates) + len(partial_dates)} files. Nothing written.")
    else:
        print(f"\nDone. {total_rows} rows upserted, {missing_rows} missing rows "
              f"detected, {len(failures)} failures.")


if __name__ == "__main__":
    main()
