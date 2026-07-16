from datetime import date, datetime

import scrapy

from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories
from Market_Scrape.utils.dates import date_to_filename, daterange
from Market_Scrape.utils.sharesansar import extract_token, parse_table, has_market_data, build_ajax_request
from Market_Scrape.utils.storage import existing_dates, save_csv
from Market_Scrape.utils.db import ensure_schema, load_daily_price_rows


class MarketMissingSpider(scrapy.Spider):
    name = "market_missing"

    start_urls = ["https://www.sharesansar.com/today-share-price"]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
    }

    DEFAULT_START_DATE = date(2010, 1, 1)

    def parse(self, response):
        ensure_directories()
        ensure_schema()

        token = extract_token(response)

        if not token:
            self.logger.error("Could not find CSRF token.")
            return

        dates = existing_dates()

        if dates:
            start_date = min(dates)
        else:
            start_date = self.DEFAULT_START_DATE

        end_date = datetime.today().date()

        for d in daterange(start_date, end_date):
            filename = date_to_filename(d)

            if (DAILY_PRICE_DIR / filename).exists():
                continue

            yield build_ajax_request(
                token=token,
                date_str=d.strftime("%Y-%m-%d"),
                callback=self.parse_day,
                date_obj=d,
            )

    def parse_day(self, response, date_obj):
        if not has_market_data(response):
            self.logger.info(f"No market data available for {date_to_filename(date_obj)}")
            return

        table_data = parse_table(response)

        if len(table_data) <= 1:
            self.logger.warning(f"Table contains no data rows for {date_to_filename(date_obj)}")
            return

        filename = date_to_filename(date_obj)

        save_csv(table_data, DAILY_PRICE_DIR / filename)

        self.logger.info(f"Saved {filename}")

        row_count = load_daily_price_rows(table_data, date_obj)
        self.logger.info(f"Upserted {row_count} rows into Postgres for {date_obj}.")