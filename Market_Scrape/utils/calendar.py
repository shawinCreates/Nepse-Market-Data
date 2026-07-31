"""
Trading-calendar helpers: which days should the spiders request data for.

NEPSE's calendar has shifted over the years (Fridays were trading days in
2022 and 2026 periods, for example), so the only reliable signal for a
closed day is ShareSansar itself saying "No Record Found". Confirmed
closed days are recorded in Data/csv/closed_days.csv and never re-requested
on subsequent runs. The one hardcoded rule is Saturday, which has never
been a NEPSE trading day.
"""

import logging
from datetime import date

from .paths import CSV_DIR, ensure_directories

logger = logging.getLogger(__name__)

CLOSED_DAYS_FILE = CSV_DIR / "closed_days.csv"


def is_saturday(d: date) -> bool:
    return d.weekday() == 5


def load_closed_days() -> set:
    """Set of dates in closed_days.csv (ISO format, one per line, with an
    optional header row). Returns an empty set if the file doesn't exist
    yet."""
    if not CLOSED_DAYS_FILE.exists():
        return set()

    closed = set()

    try:
        lines = CLOSED_DAYS_FILE.read_text().splitlines()
    except OSError:
        logger.warning("Could not read %s; treating as no closed days.", CLOSED_DAYS_FILE)
        return closed

    for line in lines:
        line = line.strip()

        if not line or line.startswith("date"):
            continue

        try:
            closed.add(date.fromisoformat(line))
        except ValueError:
            logger.warning("Ignoring unparseable closed-day entry: %r", line)

    return closed


def mark_closed_day(d: date) -> None:
    """Append a confirmed-closed day to closed_days.csv (idempotent)."""
    ensure_directories()

    if d in load_closed_days():
        return

    needs_header = not CLOSED_DAYS_FILE.exists()

    with CLOSED_DAYS_FILE.open("a") as f:
        if needs_header:
            f.write("date\n")

        f.write(f"{d.isoformat()}\n")

    logger.info("Recorded %s as a closed day in %s", d, CLOSED_DAYS_FILE)


def should_request(d: date, closed_days: set) -> bool:
    """A day is worth requesting only if it's not a Saturday and hasn't
    been confirmed closed before."""
    return not is_saturday(d) and d not in closed_days
