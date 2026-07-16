from datetime import datetime

import scrapy

from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories
from Market_Scrape.utils.dates import date_to_filename
from Market_Scrape.utils.sharesansar import extract_token, parse_table, has_market_data, build_ajax_request
from Market_Scrape.utils.storage import save_csv, is_duplicate_of_latest
from Market_Scrape.utils.db import ensure_schema, load_daily_price_rows

class MarketSpider(scrapy.Spider):
    name = "market"

    start_urls = ["https://www.sharesansar.com/today-share-price"]

    def parse(self, response):
        ensure_directories()
        ensure_schema()

        token = extract_token(response)

        if not token:
            self.logger.error("Could not find CSRF token.")
            return

        today = datetime.today().date()

        yield build_ajax_request(
            token=token,
            date_str=today.strftime("%Y-%m-%d"),
            callback=self.parse_today,
            date_obj=today,
        )

    def parse_today(self, response, date_obj):
        if not has_market_data(response):
            self.logger.info("No market data available today.")
            return

        table_data = parse_table(response)

        if len(table_data) <= 1:
            self.logger.warning("Table contains no data rows.")
            return

        filename = date_to_filename(date_obj)
        csv_path = DAILY_PRICE_DIR / filename

        if is_duplicate_of_latest(table_data, skip_file=filename):
            self.logger.info("Duplicate of latest session.")
            return

        save_csv(table_data, csv_path)

        self.logger.info(f"Saved {filename}")

        row_count = load_daily_price_rows(table_data, date_obj)
        self.logger.info(f"Upserted {row_count} rows into Postgres for {date_obj}.")