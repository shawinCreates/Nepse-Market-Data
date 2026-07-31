"""
Shared behaviour for the backfill spiders (market_history,
market_missing). Not a runnable spider on its own — subclasses provide
`name` and `first_missing_date()`.

What this handles:
  * iterating every calendar day from a start date up to today,
  * skipping Saturdays and days recorded in Data/csv/closed_days.csv,
  * requesting each missing day from ShareSansar's AJAX endpoint,
  * recording "No Record Found" days in closed_days.csv so they're never
    re-requested (NEPSE's calendar has changed over the years, so the
    source itself is the only reliable authority on which days closed),
  * re-fetching the CSRF token after a long streak of no-data responses
    (a stale token would otherwise make the rest of the run fail
    silently),
  * saving each day's CSV first, then upserting into Postgres.
"""

from datetime import datetime

import scrapy

from Market_Scrape.utils.calendar import (
    load_closed_days,
    mark_closed_day,
    should_request,
)
from Market_Scrape.utils.dates import date_to_filename, daterange
from Market_Scrape.utils.db import ensure_schema, load_daily_price_rows
from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories
from Market_Scrape.utils.sharesansar import (
    build_ajax_request,
    extract_token,
    has_market_data,
    parse_table,
)
from Market_Scrape.utils.storage import save_csv

TOKEN_REFRESH_THRESHOLD = 15


class BackfillSpider(scrapy.Spider):
    start_urls = ["https://www.sharesansar.com/today-share-price"]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
    }

    def first_missing_date(self, end_date):
        """First date to start scanning from — subclass responsibility."""
        raise NotImplementedError

    def parse(self, response):
        ensure_directories()
        ensure_schema()

        self.closed_days = load_closed_days()
        self.no_data_streak = 0

        token = extract_token(response)

        if not token:
            self.logger.error("Could not find CSRF token.")
            return

        end_date = datetime.today().date()
        start_date = response.cb_kwargs.get("resume_from") or self.first_missing_date(end_date)

        for d in daterange(start_date, end_date):
            filename = date_to_filename(d)

            if (DAILY_PRICE_DIR / filename).exists():
                continue

            if not should_request(d, self.closed_days):
                continue

            yield build_ajax_request(
                token=token,
                date_str=d.strftime("%Y-%m-%d"),
                callback=self.parse_day,
                date_obj=d,
            )

    def parse_day(self, response, date_obj):
        if response.status != 200:
            self.logger.warning(
                "HTTP %d for %s (expected 200).", response.status, date_obj
            )
            refresh = self._maybe_refresh_token(date_obj)

            if refresh is not None:
                yield refresh

            return

        if not has_market_data(response):
            self.logger.info(
                "No market data for %s — recording as a closed day.",
                date_to_filename(date_obj),
            )
            mark_closed_day(date_obj)
            self.closed_days.add(date_obj)

            refresh = self._maybe_refresh_token(date_obj)

            if refresh is not None:
                yield refresh

            return

        table_data = parse_table(response)

        if len(table_data) <= 1:
            self.logger.warning(
                "Empty table for %s — possible token expiry or page change.",
                date_to_filename(date_obj),
            )
            refresh = self._maybe_refresh_token(date_obj)

            if refresh is not None:
                yield refresh

            return

        self.no_data_streak = 0

        filename = date_to_filename(date_obj)

        save_csv(table_data, DAILY_PRICE_DIR / filename)

        self.logger.info("Saved %s", filename)

        row_count = load_daily_price_rows(table_data, date_obj)
        self.logger.info("Upserted %d rows into Postgres for %s.", row_count, date_obj)

    def _maybe_refresh_token(self, date_obj):
        """After TOKEN_REFRESH_THRESHOLD consecutive no-data responses,
        re-fetch the start page for a fresh CSRF token and resume from
        `date_obj`. Returns the refresh Request, or None."""
        self.no_data_streak += 1

        if self.no_data_streak < TOKEN_REFRESH_THRESHOLD:
            return None

        self.logger.warning(
            "Refreshing CSRF token after %d consecutive no-data responses.",
            self.no_data_streak,
        )
        self.no_data_streak = 0

        return scrapy.Request(
            self.start_urls[0],
            callback=self.parse,
            cb_kwargs={"resume_from": date_obj},
        )
