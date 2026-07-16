from datetime import date, datetime

import scrapy

from Market_Scrape.utils.paths import DAILY_PRICE_DIR, ensure_directories
from Market_Scrape.utils.dates import daterange, date_to_filename
from Market_Scrape.utils.sharesansar import extract_token, parse_table, has_market_data, build_ajax_request
from Market_Scrape.utils.storage import save_csv
from Market_Scrape.utils.db import ensure_schema, load_daily_price_rows

class MarketHistorySpider(scrapy.Spider):
    name = "market_history"

    start_urls = ["https://www.sharesansar.com/today-share-price"]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
    }

    START_DATE = date(2010, 1, 1)

    def parse(self, response):
        ensure_directories()
        ensure_schema()

        token = extract_token(response)

        if not token:
            self.logger.error("Could not find CSRF token.")
            return

        end_date = datetime.today().date()

        for d in daterange( self.START_DATE, end_date):
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