<div align="center">

```
     ▸▸  NEBL +2.4%   NABIL -0.8%   NICA +1.1%   NLIC +0.3%  ▸▸

  █   █ █████ ████   ████ █████   ████   ███  █████  ███ 
  ██  █ █     █   █ █     █       █   █ █   █   █   █   █
  █ █ █ ████  ████   ███  ████    █   █ █████   █   █████
  █  ██ █     █         █ █       █   █ █   █   █   █   █
  █   █ █████ █     ████  █████   ████  █   █   █   █   █
```

</div>

Scrapy-powered daily & historical scraper for the Nepal Stock Exchange

<div align="center">

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Scrapy](https://img.shields.io/badge/built%20with-scrapy-60c060.svg)](https://scrapy.org/)
[![Automation](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Data Range](https://img.shields.io/badge/data-2010%E2%80%93present-orange.svg)](#)

</div>

---

## Overview

A Scrapy-based scraper that pulls daily trading data for the Nepal Stock Exchange (NEPSE) from [ShareSansar](https://www.sharesansar.com/today-share-price) and stores it as date-stamped CSV files plus a consolidated Excel workbook. Designed for repeatable, automated data collection — no manual copy-paste, no missed sessions.

## Features

| Feature | Description |
|---|---|
| **Daily scraping** | One command fetches the current day's market data |
| **Historical backfill** | Scrapes every trading day from 2010 to present |
| **Gap detection** | Identifies missing dates and fetches only what's needed |
| **Duplicate detection** | Compares row data to avoid re-saving an existing session |
| **Excel export** | Combines all CSVs into a single workbook, one sheet per day |
| **Incremental updates** | Daily runs append/update only the latest sheet |
| **Rate-limited requests** | Configurable delay and concurrency per domain |
| **CI/CD automation** | Scheduled daily run via GitHub Actions, auto-commits new data |

## Project Structure

```
nepse-market-data/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml       # Daily automation (6 PM NPT)
├── Market_Scrape/
│   ├── spiders/
│   │   ├── market.py              # Daily scrape spider
│   │   ├── market_history.py      # Historical backfill spider
│   │   └── market_missing.py      # Gap-filler spider
│   └── utils/
│       ├── dates.py               # Date iteration & filename helpers
│       ├── excel.py               # Excel workbook builder & updater
│       ├── paths.py               # Centralized file path definitions
│       ├── sharesansar.py         # Token extraction, AJAX requests, HTML parsing
│       └── storage.py             # CSV save/load & duplicate detection
├── Data/
│   ├── csv/                       # Daily CSV files (YYYY_MM_DD.csv)
│   └── excel/
│       ├── combined_excel.xlsx    # Master workbook (one sheet per day)
│       └── list_of_csv_files.txt  # Index of all CSV files
├── scrapy.cfg
├── requirements.txt
└── README.md
```

## Installation

**Requirements:** Python 3.8+, pip

```bash
git clone https://github.com/shawinCreates/Nepse-Market-Data.git
cd nepse-market-data
pip install -r requirements.txt
```

## Usage

```bash
# Scrape today's market data
scrapy crawl market

# Backfill all historical data from 2010 to present
scrapy crawl market_history

# Fill in any missing dates automatically
scrapy crawl market_missing
```

## Spider Reference

| Spider | When to use | What it does | Excel behavior |
|---|---|---|---|
| `market` | Daily (cron / GitHub Action) | Fetches today's data, checks for duplicates | Incremental update |
| `market_history` | First run / backfill | Scrapes every date in a range, skipping existing files | Full rebuild on completion |
| `market_missing` | Maintenance | Finds the earliest gap and fetches forward to today | Full rebuild on completion |

## Data Format

Each CSV row contains 24 fields per stock:

| Column | Description |
|---|---|
| `S.No` | Serial number |
| `Symbol` | Stock ticker symbol |
| `Conf.` | Confidence indicator |
| `Open` | Opening price |
| `High` | Day's highest price |
| `Low` | Day's lowest price |
| `Close` | Closing price |
| `LTP` | Last traded price |
| `Close - LTP` | Difference |
| `Close - LTP %` | Percentage difference |
| `VWAP` | Volume-weighted average price |
| `Vol` | Volume (shares traded) |
| `Prev. Close` | Previous day's close |
| `Turnover` | Total turnover (NPR) |
| `Trans.` | Number of transactions |
| `Diff` | Price change |
| `Range` | Day's price range |
| `Diff %` | Price change percentage |
| `Range %` | Range percentage |
| `VWAP %` | VWAP percentage |
| `120 Days` | 120-day average |
| `180 Days` | 180-day average |
| `52 Weeks High` | 52-week high |
| `52 Weeks Low` | 52-week low |

## Configuration

Key settings in `Market_Scrape/settings.py`:

| Setting | Value | Purpose |
|---|---|---|
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 1 | One request at a time per domain |
| `DOWNLOAD_DELAY` | 1 second | Delay between requests |
| `ROBOTSTXT_OBEY` | True | Respects robots.txt |

Historical spiders override these for faster backfilling: `DOWNLOAD_DELAY = 0.5s`, `CONCURRENT_REQUESTS = 4`.

## GitHub Actions Automation

Runs automatically every day at **6:00 PM NPT**:

1. Checks out the repository
2. Installs Python dependencies
3. Runs `scrapy crawl market`
4. Commits and pushes any new/modified CSV and Excel files

Can also be triggered manually from the **Actions** tab.

## How It Works

1. **Token handshake** — visits ShareSansar's main page, extracts a CSRF token from a hidden input field
2. **AJAX request** — sends a POST request to the API endpoint with the token, target date, and sector filter
3. **Parse response** — extracts the HTML table, splits into header + data rows
4. **Save** — writes to `Data/csv/YYYY_MM_DD.csv`
5. **Excel** — rebuilds the full workbook (bulk operations) or appends the latest sheet (daily runs)

## Tech Stack

| Tool | Purpose |
|---|---|
| [Scrapy](https://scrapy.org/) | Web scraping framework |
| [pandas](https://pandas.pydata.org/) | Data manipulation & CSV/Excel I/O |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel file read/write |
| [GitHub Actions](https://github.com/features/actions) | Scheduled daily automation |

## Data Collected

| Metric | Value |
|---|---|
| Date range | 2010 – Present |
| Update frequency | Daily (automated) |
| Stocks per day | 300–500+ |
| File format | CSV (per day) + Excel (master workbook) |
| Total files | One CSV per trading day |

## License

MIT