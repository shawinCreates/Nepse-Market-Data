from datetime import datetime

import scrapy

from Market_Scrape.utils.paths import ensure_directories, overview_dir_for_date
from Market_Scrape.utils.html import parse_market_summary, parse_indices
from Market_Scrape.utils.datatable import CATEGORIES, build_datatable_request, parse_category
from Market_Scrape.utils.storage import save_overview_dict, save_overview_table
from Market_Scrape.utils.db import (
    ensure_schema,
    load_market_summary,
    load_indices,
    load_top_list,
)


class MarketOverviewSpider(scrapy.Spider):
    """Today's market snapshot: summary, indices, and the six top-15
    tables (gainers, losers, turnovers, transactions, traded shares,
    brokers).

    Unlike market.py / market_history.py, this spider only ever cares
    about the latest values — each run writes into a dated folder under
    Data/csv/overview/YYYY-MM-DD/, overwriting that day's files if run
    again, and upserts the same data into Postgres keyed on trade_date.
    """

    name = "market_overview"

    start_urls = ["https://www.sharesansar.com/market"]

    def parse(self, response):
        ensure_directories()
        ensure_schema()

        today = datetime.today().date()
        directory = overview_dir_for_date(today)

        summary = parse_market_summary(response)
        indices = parse_indices(response)

        if not summary:
            self.logger.warning("Market summary table not found or empty.")
        if not indices:
            self.logger.warning("Indices table not found or empty.")

        save_overview_dict(summary, directory, "market_summary.csv")
        save_overview_table(indices, directory, "indices.csv")

        self.logger.info(f"Saved market summary/indices to {directory}")

        summary_rows = load_market_summary(summary, today)
        self.logger.info(f"Upserted {summary_rows} market_summary rows into Postgres.")

        indices_rows = load_indices(indices, today)
        self.logger.info(f"Upserted {indices_rows} indices rows into Postgres.")

        for category in CATEGORIES.values():
            yield build_datatable_request(
                category.endpoint,
                callback=self.parse_top_list,
                cb_kwargs={
                    "category_name": category.name,
                    "directory": directory,
                    "trade_date": today,
                },
            )

    def parse_top_list(self, response, category_name, directory, trade_date):
        category = CATEGORIES[category_name]

        rows = parse_category(category, response)

        if not rows:
            self.logger.warning(f"No rows returned for {category_name}.")

        save_overview_table(rows, directory, f"top_{category_name}.csv")
        self.logger.info(f"Saved top_{category_name}.csv ({len(rows)} rows)")

        db_rows = load_top_list(category_name, rows, trade_date)
        self.logger.info(f"Upserted {db_rows} rows into top_{category_name} (Postgres).")