from datetime import date

from Market_Scrape.utils.storage import existing_dates

from .backfill_base import BackfillSpider


class MarketMissingSpider(BackfillSpider):
    name = "market_missing"

    DEFAULT_START_DATE = date(2010, 1, 1)

    def first_missing_date(self, end_date):
        dates = existing_dates()

        if dates:
            return min(dates)

        return self.DEFAULT_START_DATE
