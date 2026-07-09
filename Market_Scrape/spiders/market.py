from datetime import datetime

import scrapy

from Market_Scrape.utils.paths import CSV_DIR, ensure_directories
from Market_Scrape.utils.dates import date_to_filename
from Market_Scrape.utils.sharesansar import extract_token, parse_table, has_market_data, build_ajax_request
from Market_Scrape.utils.storage import save_csv, is_duplicate_of_latest
from Market_Scrape.utils.excel import update_latest_sheet

class MarketSpider(scrapy.Spider):
    name = "market"

    start_urls = ["https://www.sharesansar.com/today-share-price"]

    def parse(self, response):
        ensure_directories()

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
        csv_path = CSV_DIR / filename

        if is_duplicate_of_latest(table_data, skip_file=filename):
            self.logger.info("Duplicate of latest session.")
            return

        save_csv(table_data, csv_path)

        self.logger.info(f"Saved {filename}")

        update_latest_sheet()
        self.logger.info("Excel workbook updated successfully.")

