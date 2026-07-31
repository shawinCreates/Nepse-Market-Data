"""
HTML parsing for https://www.sharesansar.com/market

Unlike the top-* pages, /market renders everything server-side: Market
Summary, Indices, and Sector Performance are plain HTML tables, no AJAX
involved.
"""

from datetime import date


def _find_section_table(response, heading_keyword):
    """Find the first <table> that follows a heading containing
    `heading_keyword` (case-insensitive)."""

    lowered = (
        'translate(normalize-space(.), '
        '"ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
        '"abcdefghijklmnopqrstuvwxyz")'
    )

    heading = response.xpath(
        f'//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 '
        f'or self::div[contains(@class, "title")]]'
        f'[contains({lowered}, "{heading_keyword.lower()}")][1]'
    )

    if not heading:
        return None

    table = heading.xpath('following::table[1]')

    return table if table else None


def _table_rows(table_sel):
    if not table_sel:
        return []

    rows = table_sel.xpath('.//tr')

    table_data = []

    for row in rows:
        cells = row.xpath('.//th//text() | .//td//text()').getall()

        cells = [cell.strip() for cell in cells if cell.strip()]

        if cells:
            table_data.append(cells)

    return table_data


def parse_market_summary(response) -> dict:
    """Total Turnover / Total Traded Shares / Total Transaction /
    Total Scrips Traded / Market Cap / Floated Market Cap, as label: value.
    """
    table = _find_section_table(response, "market summary")
    rows = _table_rows(table)

    summary = {}

    for row in rows:
        if len(row) >= 2:
            summary[row[0]] = row[1]

    return summary


def parse_indices(response) -> list[dict]:
    """NEPSE / Sensitive / Float / Sensitive Float, as a list of row dicts."""
    table = _find_section_table(response, "indices")

    return _rows_with_header(table)


def _is_header_like_row(row) -> bool:
    """ShareSansar sometimes renders more than one logical table inside a
    single <table> (e.g. Indices followed by Sub-Indices), separated by a
    second header row such as:
        Sub Index,Open,High,Low,Close,Point,% Change,Turnover
    """
    return not any(
        any(ch.isdigit() for ch in cell)
        for cell in row[1:]
    )


def _rows_with_header(table_sel) -> list[dict]:
    """Treat the first row as a header and zip the rest against it.
    Rows whose cell count doesn't match the header are skipped rather
    than guessed at, so bad data never silently ends up under the wrong
    column. Repeated header rows (see _is_header_like_row) are skipped
    too, rather than being zipped in as if they were a data row."""
    rows = _table_rows(table_sel)

    if len(rows) < 2:
        return []

    header, *data_rows = rows

    return [
        dict(zip(header, row, strict=True))
        for row in data_rows
        if len(row) == len(header) and not _is_header_like_row(row)
    ]


def parse_asof_date(response) -> date | None:
    """The session date shown as "As of YYYY-MM-DD" under each section
    heading. ShareSansar keeps displaying the *previous* session's data
    on days the market is closed, so this is the only reliable way to
    tell whether the page is really showing today's session.

    The Market Summary section's "As of" span renders empty, so the
    Indices section's marker is used; falls back to the first populated
    marker anywhere on the page if the expected structure shifts.
    Returns None when no usable marker is found."""
    lowered = (
        'translate(normalize-space(.), '
        '"ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
        '"abcdefghijklmnopqrstuvwxyz")'
    )

    heading = response.xpath(
        f'//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 '
        f'or self::div[contains(@class, "title")]]'
        f'[contains({lowered}, "indices")][1]'
    )

    if heading:
        container = heading.xpath('ancestor::div[contains(@class, "col-md")][1]')
        value = container.xpath(
            './/p[contains(normalize-space(.), "As of")]'
            '/span[@class="text-org"]/text()'
        ).get()

        if value:
            return _parse_date_or_none(value)

    value = response.xpath(
        '//p[contains(normalize-space(.), "As of")]'
        '/span[@class="text-org" and normalize-space(text()) != ""][1]/text()'
    ).get()

    return _parse_date_or_none(value)


def _parse_date_or_none(value) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None
