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

Scrapy-powered daily & historical scraper for the Nepal Stock Exchange (NEPSE).

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Scrapy](https://img.shields.io/badge/built%20with-scrapy-60c060.svg)](https://scrapy.org/)
[![Automation](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)
[![Postgres](https://img.shields.io/badge/database-Postgres%20(Neon)-336791.svg)](https://neon.tech/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Data Range](https://img.shields.io/badge/data-2010%E2%80%93present-orange.svg)](#)

---

## Overview

A Scrapy-based scraper that pulls daily trading data for the Nepal Stock Exchange (NEPSE) from [ShareSansar](https://www.sharesansar.com/today-share-price). Data is stored as date-stamped CSV files and upserted into a Postgres database (Neon). Designed for repeatable, automated data collection — no manual copy-paste, no missed sessions.

The project scrapes two categories of data:

| Category | Description | Spider |
|---|---|---|
| **Daily Price** | Per-stock OHLCV data (open, high, low, close, volume, turnover, etc.) for every listed company each trading day | `market`, `market_history`, `market_missing` |
| **Market Overview** | Daily market snapshot: summary stats, index values, and top-15 lists (gainers, losers, turnovers, transactions, traded shares, brokers) | `market_overview` |

## Features

| Feature | Description |
|---|---|
| **Daily scraping** | One command fetches the current day's market data |
| **Historical backfill** | Scrapes every trading day from 2010 to present |
| **Gap detection** | Identifies missing dates and fetches only what's needed |
| **Market overview** | Captures daily summary, indices, and top-15 lists |
| **Duplicate detection** | Compares row data to avoid re-saving an identical session |
| **CSV storage** | One file per trading day under `Data/csv/daily_price/` |
| **Postgres integration** | Upserts all scraped data into a Neon (Postgres) database |
| **DB backfill script** | Loads existing CSV files into Postgres without re-fetching |
| **Rate-limited requests** | Configurable delay and concurrency per domain |
| **CI/CD automation** | Scheduled daily run via GitHub Actions, auto-commits new data |
| **Schema migration** | Database tables auto-adjust to schema changes on each run |

## Project Structure

```
nepse-market-data/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml          # Daily automation (4:00 PM NPT)
├── Market_Scrape/
│   ├── spiders/
│   │   ├── market.py                 # Daily price scrape spider
│   │   ├── market_history.py         # Historical backfill spider (2010–present)
│   │   ├── market_missing.py         # Gap-filler spider
│   │   └── market_overview.py        # Market snapshot spider
│   ├── utils/
│   │   ├── ajax.py                   # AJAX helpers for today-share-price endpoint
│   │   ├── datatable.py              # DataTables client for top-* endpoints
│   │   ├── dates.py                  # Date iteration & filename helpers
│   │   ├── db.py                     # Postgres (Neon) database loader
│   │   ├── html.py                   # HTML parsing for /market page
│   │   ├── paths.py                  # Centralized file path definitions
│   │   ├── sharesansar.py            # Backward-compatible re-export shim
│   │   └── storage.py                # CSV save/load & duplicate detection
│   ├── items.py                      # Scrapy item definitions (placeholder)
│   ├── middlewares.py                # Scrapy middleware stubs
│   ├── pipelines.py                  # Scrapy pipeline stubs
│   └── settings.py                   # Scrapy project settings
├── Data/
│   ├── csv/
│   │   ├── daily_price/              # Daily CSV files (YYYY_MM_DD.csv)
│   │   └── overview/                 # Market overview snapshots
│   │       └── YYYY-MM-DD/           # Per-day overview files
│   │           ├── market_summary.csv
│   │           ├── indices.csv
│   │           ├── top_gainers.csv
│   │           ├── top_losers.csv
│   │           ├── top_turnovers.csv
│   │           ├── top_transactions.csv
│   │           ├── top_tradedshares.csv
│   │           └── top_brokers.csv
├── backfilldb.py                     # One-time DB backfill from existing CSVs
├── scrapy.cfg
├── requirements.txt
├── env.example                       # Environment variable template
└── README.md
```

## Installation

**Requirements:** Python 3.8+, pip

```bash
git clone https://github.com/shawinCreates/Nepse-Market-Data.git
cd nepse-market-data
pip install -r requirements.txt
```

### Database Setup (Optional)

The project supports Postgres (Neon) for persistent storage. To enable it:

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```
2. Set your `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
   ```
3. The database schema is auto-created on every spider run — no manual migration needed.

If `DATABASE_URL` is not set, the spiders still scrape and save CSV files; only the Postgres upsert step is skipped.

## Usage

```bash
# Scrape today's market data (daily prices)
scrapy crawl market

# Scrape today's market overview (summary, indices, top-15 lists)
scrapy crawl market_overview

# Backfill all historical data from 2010 to present
scrapy crawl market_history

# Fill in any missing dates automatically
scrapy crawl market_missing

# Load existing CSV files into Postgres (no network requests)
python backfilldb.py
```

## Spider Reference

| Spider | When to use | What it scrapes | CSV output | DB output |
|---|---|---|---|---|
| `market` | Daily (cron / GitHub Action) | Today's per-stock OHLCV data | `Data/csv/daily_price/YYYY_MM_DD.csv` | Upserts into `daily_price` table |
| `market_history` | First run / backfill | Every trading day from 2010, skipping existing files | One CSV per day | Upserts into `daily_price` table |
| `market_missing` | Maintenance | Finds the earliest gap and fetches forward to today | One CSV per missing day | Upserts into `daily_price` table |
| `market_overview` | Daily (runs alongside `market`) | Market summary, indices, top gainers/losers/turnovers/transactions/traded shares/brokers | `Data/csv/overview/YYYY-MM-DD/*.csv` (8 files) | Upserts into `market_summary`, `indices`, `top_*` tables |

## Data Format

### Daily Price CSV

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

### Market Overview Files

| File | Contents |
|---|---|
| `market_summary.csv` | Total Turnover, Total Traded Shares, Total Transactions, Total Scrips Traded, Market Cap, Floated Market Cap |
| `indices.csv` | NEPSE, Sensitive, Float, Sensitive Float indices with OHLC and change values |
| `top_gainers.csv` | Top 15 gainers (symbol, company, close, change, change %) |
| `top_losers.csv` | Top 15 losers (symbol, company, close, change, change %) |
| `top_turnovers.csv` | Top 15 by turnover (symbol, company, turnover, LTP) |
| `top_transactions.csv` | Top 15 by transactions (symbol, company, transactions, LTP) |
| `top_tradedshares.csv` | Top 15 by traded volume (symbol, company, volume, LTP) |
| `top_brokers.csv` | Top 15 brokers (code, name, purchase/sales/total amounts, difference, matching amount) |

## Database Schema

The project creates and manages the following Postgres tables (auto-created on first run):

| Table | Primary Key | Description |
|---|---|---|
| `daily_price` | `(trade_date, symbol)` | Historical OHLCV data, one row per symbol per trading day |
| `market_summary` | `(trade_date, label)` | Daily market summary statistics |
| `indices` | `(trade_date, index_name)` | NEPSE and sub-index values |
| `top_gainers` | `(trade_date, symbol)` | Top 15 gainers |
| `top_losers` | `(trade_date, symbol)` | Top 15 losers |
| `top_turnovers` | `(trade_date, symbol)` | Top 15 by turnover |
| `top_transactions` | `(trade_date, symbol)` | Top 15 by transactions |
| `top_tradedshares` | `(trade_date, symbol)` | Top 15 by traded volume |
| `top_brokers` | `(trade_date, broker_code)` | Top 15 brokers |

All tables use `ON CONFLICT ... DO UPDATE` upsert semantics, making repeated runs idempotent.

## Configuration

### Scrapy Settings (`Market_Scrape/settings.py`)

| Setting | Value | Purpose |
|---|---|---|
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 1 | One request at a time per domain |
| `DOWNLOAD_DELAY` | 1 second | Delay between requests |
| `ROBOTSTXT_OBEY` | True | Respects robots.txt |

Historical spiders (`market_history`, `market_missing`) override these for faster backfilling: `DOWNLOAD_DELAY = 0.5s`, `CONCURRENT_REQUESTS = 4`.

### Environment Variables (`env.example`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | No (CSV-only mode if unset) | Postgres connection string (e.g., Neon) |

## GitHub Actions Automation

Runs automatically every day at **4:00 PM NPT** (12:15 UTC):

1. Checks out the repository
2. Installs Python dependencies
3. Runs `scrapy crawl market` (daily prices)
4. Runs `scrapy crawl market_overview` (market snapshot)
5. Commits and pushes any new/modified CSV files

Can also be triggered manually from the **Actions** tab.

## How It Works

### Daily Price Scraping

1. **Token handshake** — visits ShareSansar's main page, extracts a CSRF token from a hidden input field
2. **AJAX request** — sends a POST request to the API endpoint with the token, target date, and sector filter
3. **Parse response** — extracts the HTML table, splits into header + data rows
4. **Save CSV** — writes to `Data/csv/daily_price/YYYY_MM_DD.csv`
5. **Upsert to DB** — loads the parsed rows into the `daily_price` Postgres table

### Market Overview Scraping

1. **HTML parsing** — visits `/market` page, parses server-rendered Market Summary and Indices tables
2. **DataTables requests** — sends JSON requests to six top-* endpoints (gainers, losers, turnovers, transactions, traded shares, brokers)
3. **Save CSVs** — writes 8 files to `Data/csv/overview/YYYY-MM-DD/`
4. **Upsert to DB** — loads data into `market_summary`, `indices`, and `top_*` tables

### Duplicate Detection

The daily spider compares the current day's data against the most recent CSV file. If the data is identical (ignoring serial numbers), the file is not re-saved — preventing unnecessary commits in the automated pipeline.

### Schema Flexibility

The `daily_price` table uses a header-alias mapping system that handles ShareSansar's column changes over 15+ years of history. Columns that don't exist in a given day's response are stored as NULL, and unknown columns are silently ignored.

## Tech Stack

| Tool | Purpose |
|---|---|
| [Scrapy](https://scrapy.org/) | Web scraping framework |
| [pandas](https://pandas.pydata.org/) | Data manipulation & CSV I/O |
| [psycopg2](https://www.psycopg.org/) | Postgres database adapter |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Environment variable loading |
| [Neon](https://neon.tech/) | Serverless Postgres hosting |
| [GitHub Actions](https://github.com/features/actions) | Scheduled daily automation |

## Data Collected

| Metric | Value |
|---|---|
| Date range | 2010 – Present |
| Update frequency | Daily (automated) |
| Stocks per day | 300–500+ |
| File format | CSV (per day) + Postgres database |
| Total files | One CSV per trading day + 8 overview files per day |

## License

MIT