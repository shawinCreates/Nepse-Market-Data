"""
Generic client for ShareSansar's jQuery-DataTables-backed endpoints:

    /top-transactions
    /top-turnovers
    /top-tradedshares
    /top-losers
    /top-gainers
    /top-brokers

These pages render an empty table shell in HTML; the actual rows are
fetched client-side as JSON from the *same URL*, distinguished only by the
X-Requested-With / Accept headers and a handful of DataTables query
params (draw/start/length). See DATATABLE_HEADERS below.
"""

from dataclasses import dataclass, field

from scrapy import Request, Selector
from urllib.parse import urlencode
from datetime import datetime

BASE_URL = "https://www.sharesansar.com"

DATATABLE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def extract_text(html_fragment):
    """ShareSansar returns cell values as raw HTML, e.g.

        "<a href='.../company/corbl'>CORBL</a>"

    Pull out the human-readable text (falls back to the raw fragment if
    there's no markup to strip, e.g. plain numeric cells).
    """
    if not html_fragment:
        return None

    text = Selector(text=html_fragment).xpath("string(.)").get()

    return text.strip() if text else html_fragment.strip()


def extract_href(html_fragment):
    """Pull the linked URL out of a cell like extract_text() does for text."""
    if not html_fragment:
        return None

    return Selector(text=html_fragment).xpath("//a/@href").get()


def build_datatable_request(endpoint, callback, cb_kwargs=None, length=15):
    params = {
        "draw": 1,
        "start": 0,
        "length": length,
    }

    if endpoint == "top-brokers":
        params = {
            "draw": 1,
            "start": 0,
            "length": 15,

            "columns[0][data]": "DT_Row_Index",
            "columns[1][data]": "number",
            "columns[2][data]": "name",
            "columns[3][data]": "buyerAmount",
            "columns[4][data]": "sellerAmount",
            "columns[5][data]": "totalAmount",
            "columns[6][data]": "differ",
            "columns[7][data]": "matchingAmount",

            "order[0][column]": 5,
            "order[0][dir]": "desc",

            "search[value]": "",
            "search[regex]": "false",

            "date": datetime.today().strftime("%Y-%m-%d"),
        }

    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"

    return Request(
        url,
        headers={
            **DATATABLE_HEADERS,
            "Referer": f"{BASE_URL}/{endpoint}",
        },
        callback=callback,
        cb_kwargs=cb_kwargs or {},
    )


def parse_datatable_envelope(response):
    """Unwrap the {draw, recordsTotal, recordsFiltered, data} envelope.

    Returns (rows, records_total) where rows is the raw list of dicts
    straight from JSON (values may still contain embedded HTML — use
    extract_text/extract_href, or a category parser, to clean them up).
    """
    payload = response.json()

    rows = payload.get("data", [])
    records_total = payload.get("recordsTotal", len(rows))

    return rows, records_total


@dataclass
class Category:
    """Describes one top-* table: where to fetch it and how to read a row."""

    name: str
    endpoint: str
    row_parser: "callable"


def parse_gainers_row(row, rank):
    return {
        "rank": rank,
        "symbol": extract_text(row.get("symbol")),
        "company_name": extract_text(row.get("companyname")),
        "close": row.get("close"),
        "change": row.get("change_pts") or row.get("point_change"),
        "change_percent": row.get("diff_per") or row.get("percent_change"),
    }


def parse_losers_row(row, rank):
    # Same shape as gainers — ShareSansar renders both tables from the
    # same underlying column set, just sorted in the opposite direction.
    return parse_gainers_row(row, rank)


def parse_turnovers_row(row, rank):
    return {
        "rank": rank,
        "symbol": extract_text(row.get("symbol")),
        "company_name": extract_text(row.get("companyname")),
        "turnover": row.get("traded_amount"),
        "ltp": row.get("ltp") or row.get("close"),
    }


def parse_transactions_row(row, rank):
    return {
        "rank": rank,
        "symbol": extract_text(row.get("symbol")),
        "company_name": extract_text(row.get("companyname")),
        "transactions": row.get("no_trade"),
        "ltp": row.get("close"),
    }


def parse_tradedshares_row(row, rank):
    return {
        "rank": rank,
        "symbol": extract_text(row.get("symbol")),
        "company_name": extract_text(row.get("companyname")),
        "volume": row.get("traded_quantity"),
        "ltp": row.get("close"),
    }


def parse_brokers_row(row, rank):
    return {
        "rank": rank,
        "broker_code": row.get("number"),
        "broker_name": extract_text(row.get("name")),
        "purchase_amount": row.get("buyerAmount"),
        "sales_amount": row.get("sellerAmount"),
        "total_amount": row.get("totalAmount"),
        "difference": row.get("differ"),
        "matching_amount": row.get("matchingAmount"),
    }


CATEGORIES = {
    "gainers": Category("gainers", "top-gainers", parse_gainers_row),
    "losers": Category("losers", "top-losers", parse_losers_row),
    "turnovers": Category("turnovers", "top-turnovers", parse_turnovers_row),
    "transactions": Category("transactions", "top-transactions", parse_transactions_row),
    "tradedshares": Category("tradedshares", "top-tradedshares", parse_tradedshares_row),
    "brokers": Category("brokers", "top-brokers", parse_brokers_row),
}


def parse_category(category: Category, response):
    """Fetch + parse one category's response into a clean list[dict]."""
    rows, _ = parse_datatable_envelope(response)

    return [
        category.row_parser(row, rank=i + 1)
        for i, row in enumerate(rows)
    ]