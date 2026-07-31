from datetime import date

from .backfill_base import BackfillSpider


class MarketHistorySpider(BackfillSpider):
    name = "market_history"

    START_DATE = date(2010, 1, 1)

    def first_missing_date(self, end_date):
        return self.START_DATE
