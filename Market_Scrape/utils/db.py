"""
Loads scraped data into Postgres (Neon), so the CSVs under Data/csv/ and
the database always reflect the same source of truth.

DATABASE_URL is read from the environment (via a local .env file, loaded
with python-dotenv). Never hardcode the connection string here — .env
must stay out of git (see .gitignore).

Layout of this file, one section per table (or table group):

    connection / shared helpers   — get_connection, ensure_schema, value
                                     cleaning, the shared upsert() helper
    daily_price                   — historical OHLCV, one row per
                                     symbol per trading day
    market_summary                — today's label/value market stats
    indices                       — today's NEPSE/sub-indices
    top_* (six tables)             — today's top-15 lists, driven by
                                     CATEGORY_SCHEMAS

Public API (what spiders/scripts actually call):
    ensure_schema()
    load_daily_price_rows(table_data, trade_date)
    load_market_summary(summary, trade_date)
    load_indices(rows, trade_date)
    load_top_list(category_name, rows, trade_date)

Everything else (leading underscore, or the SQL/schema constants) is
internal to this module.
"""

import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import execute_values

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")

logger = logging.getLogger(__name__)


# === Connection + shared helpers ===========================================

@contextmanager
def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to a .env file "
            "(DATABASE_URL=postgresql://...) or export it in the shell."
        )

    conn = psycopg2.connect(DATABASE_URL)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dedupe_by_key(values: list, key_indices: tuple) -> list:
    """Postgres rejects a single INSERT ... ON CONFLICT DO UPDATE if two
    rows in the *same statement* target the same conflict key (raises
    CardinalityViolation: "ON CONFLICT DO UPDATE command cannot affect
    row a second time") — this is different from running the same day
    twice across separate runs, which upserts fine. It happens for real:
    some old ShareSansar-scraped days contain the same symbol twice.
    Collapses same-key rows to the last occurrence before the batch ever
    reaches Postgres, so one bad day can't fail the whole batch."""
    deduped = {tuple(row[i] for i in key_indices): row for row in values}

    if len(deduped) < len(values):
        logger.warning(
            "Dropped %d duplicate-key row(s) within the same batch "
            "before upserting (kept the last occurrence of each).",
            len(values) - len(deduped),
        )

    return list(deduped.values())


def _upsert(sql: str, values: list, key_indices: tuple) -> int:
    """Shared tail end of every load_*() function below: dedupe any
    same-batch conflict-key collisions (see _dedupe_by_key), skip the
    round trip entirely if there's nothing to write, otherwise
    execute_values() the upsert and report how many rows went in."""
    if not values:
        return 0

    values = _dedupe_by_key(values, key_indices)

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, values)

    return len(values)


def _clean_number(value):
    """"1,234.56" -> 1234.56 ; "-" / "" / "N/A" -> None."""
    if value is None:
        return None

    v = value.strip().replace(",", "")

    if v in ("", "-", "N/A", "NA"):
        return None

    try:
        return float(v)
    except ValueError:
        return None


def _coerce_numeric(value):
    """Like _clean_number, but tolerant of values that are already an
    int/float (e.g. `rank`, which datatable.py produces as a plain int
    rather than a scraped string)."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    return _clean_number(str(value))


def _normalize_header(key: str) -> str:
    """"Close - LTP %" -> "closeltppct", "S.No" -> "sno". Preserves the
    "%" as "pct" (rather than just stripping it) so e.g. "Close - LTP"
    and "Close - LTP %" don't collide once punctuation is removed."""
    k = key.strip().lower().replace("%", "pct")

    return "".join(ch for ch in k if ch.isalnum())


def ensure_schema():
    """Create every table this module writes to if it doesn't exist yet,
    and bring the top_* tables' columns in line with CATEGORY_SCHEMAS if
    they were created by an older version of this file (see
    _category_migration_sql). Safe to call on every spider run."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(DAILY_PRICE_CREATE_SQL)
            cur.execute(MARKET_SUMMARY_CREATE_SQL)
            cur.execute(INDICES_CREATE_SQL)

            for schema in CATEGORY_SCHEMAS.values():
                cur.execute(_category_create_sql(schema))

                for statement in _category_migration_sql(schema):
                    cur.execute(statement)


# === daily_price =============================================================
#
# Historical OHLCV, one row per symbol per trading day. Fed by
# parse_table() in utils/ajax.py, via market.py / market_history.py /
# market_missing.py / backfill_db.py.

# DB columns, in the order they're inserted (trade_date + symbol first;
# "serial"/S.No isn't stored — trade_date+symbol is the key).
DAILY_PRICE_COLUMNS = [
    "trade_date", "symbol", "conf", "open", "high", "low", "close", "ltp",
    "close_ltp_diff", "close_ltp_percent", "vwap", "volume", "prev_close",
    "turnover", "transactions", "diff", "range", "diff_percent",
    "range_percent", "vwap_percent", "avg_120_days", "avg_180_days",
    "week52_high", "week52_low",
]

# ShareSansar's table layout has changed over the ~15 years of scraped
# history (columns added/reordered), so older CSVs don't reliably have
# the same column count as today's. Rather than assume a fixed position,
# each file's own header row is read and matched against these aliases —
# any header column this maps to nothing is ignored, and any DB column
# with no match in a given file's header is stored as NULL rather than
# the row being dropped.
DAILY_PRICE_HEADER_ALIASES = {
    "sno": "serial",  # not stored; only used to confirm a real header row
    "symbol": "symbol",
    "conf": "conf",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "ltp": "ltp",
    "closeltp": "close_ltp_diff",
    "closeltppct": "close_ltp_percent",
    "vwap": "vwap",
    "vol": "volume",
    "prevclose": "prev_close",
    "turnover": "turnover",
    "trans": "transactions",
    "diff": "diff",
    "range": "range",
    "diffpct": "diff_percent",
    "rangepct": "range_percent",
    "vwappct": "vwap_percent",
    "120days": "avg_120_days",
    "180days": "avg_180_days",
    "52weekshigh": "week52_high",
    "52weekslow": "week52_low",
}

DAILY_PRICE_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS daily_price (
    trade_date          DATE NOT NULL,
    symbol              TEXT NOT NULL,
    conf                TEXT,
    open                NUMERIC,
    high                NUMERIC,
    low                 NUMERIC,
    close               NUMERIC,
    ltp                 NUMERIC,
    close_ltp_diff      NUMERIC,
    close_ltp_percent   NUMERIC,
    vwap                NUMERIC,
    volume              BIGINT,
    prev_close          NUMERIC,
    turnover            NUMERIC,
    transactions        BIGINT,
    diff                NUMERIC,
    range               NUMERIC,
    diff_percent        NUMERIC,
    range_percent       NUMERIC,
    vwap_percent        NUMERIC,
    avg_120_days        NUMERIC,
    avg_180_days        NUMERIC,
    week52_high         NUMERIC,
    week52_low          NUMERIC,
    PRIMARY KEY (trade_date, symbol)
);
"""

DAILY_PRICE_UPSERT_SQL = f"""
INSERT INTO daily_price ({", ".join(DAILY_PRICE_COLUMNS)})
VALUES %s
ON CONFLICT (trade_date, symbol) DO UPDATE SET
    {", ".join(f"{c} = EXCLUDED.{c}" for c in DAILY_PRICE_COLUMNS if c not in ("trade_date", "symbol"))}
;
"""


def _daily_price_header_index(header: list) -> dict:
    """Map canonical column name -> index in this file's header row.
    Built once per file (not per row) since the header is the same for
    every row in a CSV."""
    index = {}

    for i, raw_name in enumerate(header):
        canonical = DAILY_PRICE_HEADER_ALIASES.get(_normalize_header(raw_name))

        if canonical:
            index[canonical] = i

    return index


def _daily_price_row_values(row, trade_date, col_index: dict):
    """row is one data row from parse_table(). col_index maps canonical
    column name -> position in `row`, built from this file's own header
    via _daily_price_header_index() — so files with fewer/reordered
    columns (older scrapes, before ShareSansar added a column) still map
    correctly, just with NULLs for whatever that file doesn't have.
    Returns a tuple in DAILY_PRICE_COLUMNS order, or None if there's no
    symbol to key on."""

    def cell(col):
        i = col_index.get(col)
        return row[i] if i is not None and i < len(row) else None

    symbol_raw = cell("symbol")
    symbol = symbol_raw.strip() if symbol_raw else ""

    if not symbol:
        return None

    values = [trade_date, symbol]

    for col in DAILY_PRICE_COLUMNS[2:]:
        raw = cell(col)

        if col in ("volume", "transactions"):
            cleaned = _clean_number(raw)
            values.append(int(cleaned) if cleaned is not None else None)
        elif col == "conf":
            values.append(raw.strip() if raw else None)
        else:
            values.append(_clean_number(raw))

    return tuple(values)


def load_daily_price_rows(table_data, trade_date) -> int:
    """table_data is the list-of-lists from parse_table() — header row
    first, data rows after. Upserts every valid data row into Postgres.
    Returns the number of rows written."""
    if not table_data:
        return 0

    header, *data_rows = table_data

    col_index = _daily_price_header_index(header)

    if "symbol" not in col_index:
        # Nothing in this file's header looks like a Symbol column at
        # all — mapping would silently write zero rows, so surface it
        # instead of pretending everything's fine.
        raise ValueError(
            "Could not find a 'Symbol' column in this file's header: "
            f"{header!r}"
        )

    values = [
        v
        for v in (
            _daily_price_row_values(row, trade_date, col_index)
            for row in data_rows
        )
        if v is not None
    ]

    return _upsert(DAILY_PRICE_UPSERT_SQL, values, key_indices=(0, 1))


# === market_summary ==========================================================
#
# Today's label/value market stats (Total Turnover, Total Traded Shares,
# ...). Fed by parse_market_summary() in utils/market.py, via
# market_overview.py.

MARKET_SUMMARY_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS market_summary (
    trade_date  DATE NOT NULL,
    label       TEXT NOT NULL,
    value       TEXT,
    PRIMARY KEY (trade_date, label)
);
"""

MARKET_SUMMARY_UPSERT_SQL = """
INSERT INTO market_summary (trade_date, label, value)
VALUES %s
ON CONFLICT (trade_date, label) DO UPDATE SET
    value = EXCLUDED.value
;
"""


def load_market_summary(summary: dict, trade_date) -> int:
    """summary is the label->value dict from parse_market_summary()."""
    values = [
        (trade_date, str(label).strip(), None if value is None else str(value).strip())
        for label, value in summary.items()
    ]

    return _upsert(MARKET_SUMMARY_UPSERT_SQL, values, key_indices=(0, 1))


# === indices ==================================================================
#
# Today's NEPSE index + sub-indices. Fed by parse_indices() in
# utils/market.py, via market_overview.py.

INDICES_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS indices (
    trade_date      DATE NOT NULL,
    index_name      TEXT NOT NULL,
    open            NUMERIC,
    high            NUMERIC,
    low             NUMERIC,
    close           NUMERIC,
    point_change    NUMERIC,
    percent_change  NUMERIC,
    turnover        NUMERIC,
    PRIMARY KEY (trade_date, index_name)
);
"""

INDICES_UPSERT_SQL = """
INSERT INTO indices
    (trade_date, index_name, open, high, low, close,
     point_change, percent_change, turnover)
VALUES %s
ON CONFLICT (trade_date, index_name) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    point_change = EXCLUDED.point_change,
    percent_change = EXCLUDED.percent_change,
    turnover = EXCLUDED.turnover
;
"""

# Maps a normalized header key (see _normalize_header) to the indices
# table's column name. Handles the page rendering headers as "Point
# Change" / "% Change" rather than exactly matching the DB's snake_case
# names.
INDICES_HEADER_MAP = {
    "index": "index_name",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "pointchange": "point_change",
    "point": "point_change",
    "pctchange": "percent_change",
    "change": "percent_change",
    "turnover": "turnover",
}


def load_indices(rows: list, trade_date) -> int:
    """rows is the list[dict] from parse_indices() — dict keys are
    whatever header text the page rendered ("Index", "Point Change", ...)."""
    values = []

    for row in rows:
        mapped = {}

        for key, value in row.items():
            db_col = INDICES_HEADER_MAP.get(_normalize_header(key))

            if db_col:
                mapped[db_col] = value

        index_name = mapped.get("index_name")

        if not index_name:
            continue

        values.append((
            trade_date,
            str(index_name).strip(),
            _clean_number(mapped.get("open")),
            _clean_number(mapped.get("high")),
            _clean_number(mapped.get("low")),
            _clean_number(mapped.get("close")),
            _clean_number(mapped.get("point_change")),
            _clean_number(mapped.get("percent_change")),
            _clean_number(mapped.get("turnover")),
        ))

    return _upsert(INDICES_UPSERT_SQL, values, key_indices=(0, 1))


# === top_* (six tables) ======================================================
#
# Today's top-15 lists (gainers/losers/turnovers/transactions/
# tradedshares/brokers), one table each. Fed by datatable.parse_category()
# in utils/datatable.py, via market_overview.py.
#
# Each entry below is the single source of truth for its table: `columns`
# must match the keys produced by the matching parse_*_row() function in
# datatable.py, and `column_types`/`create_sql`/the ALTER statements are
# all generated from it, so the DB schema can't quietly drift out of sync
# with what the parser actually produces.
#
# `obsolete_columns` lists columns a *previous* version of this schema
# created that no longer correspond to anything datatable.py produces —
# ensure_schema() drops them so an already-existing table converges to
# the current shape instead of just accumulating unused columns forever.
# `integer_cols` marks numeric columns that should be stored as a real
# int (BIGINT columns like transactions/volume) rather than a float.

CATEGORY_SCHEMAS = {
    "gainers": {
        "table": "top_gainers",
        "columns": ["rank", "symbol", "company_name", "close", "change", "change_percent"],
        "column_types": {
            "rank": "INTEGER", "symbol": "TEXT NOT NULL", "company_name": "TEXT",
            "close": "NUMERIC", "change": "NUMERIC", "change_percent": "NUMERIC",
        },
        "numeric_cols": {"close", "change", "change_percent"},
        "conflict_cols": ["trade_date", "symbol"],
        "obsolete_columns": [],
    },
    "losers": {
        "table": "top_losers",
        "columns": ["rank", "symbol", "company_name", "close", "change", "change_percent"],
        "column_types": {
            "rank": "INTEGER", "symbol": "TEXT NOT NULL", "company_name": "TEXT",
            "close": "NUMERIC", "change": "NUMERIC", "change_percent": "NUMERIC",
        },
        "numeric_cols": {"close", "change", "change_percent"},
        "conflict_cols": ["trade_date", "symbol"],
        "obsolete_columns": [],
    },
    "turnovers": {
        "table": "top_turnovers",
        "columns": ["rank", "symbol", "company_name", "turnover", "ltp"],
        "column_types": {
            "rank": "INTEGER", "symbol": "TEXT NOT NULL", "company_name": "TEXT",
            "turnover": "NUMERIC", "ltp": "NUMERIC",
        },
        "numeric_cols": {"turnover", "ltp"},
        "conflict_cols": ["trade_date", "symbol"],
        "obsolete_columns": ["change_percent"],
    },
    "transactions": {
        "table": "top_transactions",
        "columns": ["rank", "symbol", "company_name", "transactions", "ltp"],
        "column_types": {
            "rank": "INTEGER", "symbol": "TEXT NOT NULL", "company_name": "TEXT",
            "transactions": "BIGINT", "ltp": "NUMERIC",
        },
        "numeric_cols": {"transactions", "ltp"},
        "integer_cols": {"transactions"},
        "conflict_cols": ["trade_date", "symbol"],
        "obsolete_columns": ["shares_traded", "turnover"],
    },
    "tradedshares": {
        "table": "top_tradedshares",
        "columns": ["rank", "symbol", "company_name", "volume", "ltp"],
        "column_types": {
            "rank": "INTEGER", "symbol": "TEXT NOT NULL", "company_name": "TEXT",
            "volume": "BIGINT", "ltp": "NUMERIC",
        },
        "numeric_cols": {"volume", "ltp"},
        "integer_cols": {"volume"},
        "conflict_cols": ["trade_date", "symbol"],
        "obsolete_columns": ["shares_traded", "turnover", "transactions"],
    },
    "brokers": {
        "table": "top_brokers",
        "columns": [
            "rank", "broker_code", "broker_name", "purchase_amount",
            "sales_amount", "total_amount", "difference", "matching_amount",
        ],
        "column_types": {
            "rank": "INTEGER", "broker_code": "TEXT NOT NULL", "broker_name": "TEXT",
            "purchase_amount": "NUMERIC", "sales_amount": "NUMERIC",
            "total_amount": "NUMERIC", "difference": "NUMERIC",
            "matching_amount": "NUMERIC",
        },
        "numeric_cols": {
            "purchase_amount", "sales_amount", "total_amount",
            "difference", "matching_amount",
        },
        "conflict_cols": ["trade_date", "broker_code"],
        "obsolete_columns": [],
    },
}


def _category_create_sql(schema) -> str:
    cols_sql = ",\n                ".join(
        f"{col} {schema['column_types'][col]}" for col in schema["columns"]
    )
    pk = ", ".join(schema["conflict_cols"])

    return f"""
        CREATE TABLE IF NOT EXISTS {schema["table"]} (
            trade_date DATE NOT NULL,
                {cols_sql},
            PRIMARY KEY ({pk})
        );
    """


def _category_migration_sql(schema) -> list:
    """ALTER statements that bring an already-existing table (possibly
    created by an older version of this schema) in line with the current
    one. Safe to run every time — IF NOT EXISTS / IF EXISTS make every
    statement a no-op once the table already matches."""
    statements = []

    for col in schema["columns"]:
        # NOT NULL can't be added via ALTER ... ADD COLUMN if the table
        # already has rows (there'd be no value to backfill existing
        # rows with), so the added column is nullable; the NOT NULL only
        # applies when the table is created fresh via CREATE TABLE above.
        col_type = schema["column_types"][col].replace(" NOT NULL", "")
        statements.append(
            f"ALTER TABLE {schema['table']} ADD COLUMN IF NOT EXISTS {col} {col_type};"
        )

    for col in schema["obsolete_columns"]:
        statements.append(
            f"ALTER TABLE {schema['table']} DROP COLUMN IF EXISTS {col};"
        )

    return statements


def _category_upsert_sql(schema) -> str:
    all_cols = ["trade_date"] + schema["columns"]
    update_cols = [c for c in all_cols if c not in schema["conflict_cols"]]

    return f"""
        INSERT INTO {schema["table"]} ({", ".join(all_cols)})
        VALUES %s
        ON CONFLICT ({", ".join(schema["conflict_cols"])}) DO UPDATE SET
            {", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)}
        ;
    """


def load_top_list(category_name: str, rows: list, trade_date) -> int:
    """rows is the list[dict] from datatable.parse_category() for one of
    gainers/losers/turnovers/transactions/tradedshares/brokers."""
    schema = CATEGORY_SCHEMAS[category_name]

    values = []

    for row in rows:
        record = [trade_date]

        for col in schema["columns"]:
            raw = row.get(col)

            if col == "rank" or col in schema.get("integer_cols", set()):
                cleaned = _coerce_numeric(raw)
                record.append(int(cleaned) if cleaned is not None else None)
            elif col in schema["numeric_cols"]:
                record.append(_coerce_numeric(raw))
            elif raw is not None:
                record.append(str(raw).strip())
            else:
                record.append(None)

        values.append(tuple(record))

    all_cols = ["trade_date"] + schema["columns"]
    key_indices = tuple(all_cols.index(c) for c in schema["conflict_cols"])

    return _upsert(_category_upsert_sql(schema), values, key_indices=key_indices)