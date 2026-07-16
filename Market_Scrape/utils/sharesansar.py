"""
Backward-compatible shim.

All logic that used to live here has moved to ajax.py as part of splitting
the utility layer by response type (ajax / datatable / market-html) instead
of growing one big sharesansar.py file. Existing spiders keep working
unchanged because the same names are still importable from here.

New code should import from Market_Scrape.utils.ajax directly.
"""

from .ajax import (
    extract_token,
    has_market_data,
    parse_table,
    build_ajax_request,
)

__all__ = [
    "extract_token",
    "has_market_data",
    "parse_table",
    "build_ajax_request",
]