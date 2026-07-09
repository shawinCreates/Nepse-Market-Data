# 📈 NEPSE Market Data Scraper

> **Automated daily & historical stock data from Nepal Stock Exchange — straight to your CSV and Excel.**

A Scrapy-powered web scraper that pulls live trading data from [ShareSansar](https://www.sharesansar.com/today-share-price) and organizes it into clean, date-stamped CSV files and a master Excel workbook. Built for analysts, traders, and anyone who wants NEPSE data without the manual copy-paste.

---

## ✨ Features

- **Daily scraping** — One command fetches today's market data automatically
- **Historical backfill** — Scrape every trading day from 2010 to present
- **Smart gap-filling** — Detect missing dates and fetch only what's needed
- **Duplicate detection** — Compares data rows to avoid saving the same trading session twice
- **Excel export** — All CSVs combined into a single workbook, one sheet per day
- **Incremental updates** — Daily runs only add/update the latest sheet (no full rebuild)
- **Polite scraping** — Configurable delays and concurrency to respect the server
- **GitHub Actions automation** — Scheduled daily scrape at 6 PM NPT, auto-commits new data

---

## 🧱 Project Structure

```
nepse-market-data/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml       # 🤖 Daily automation (6 PM NPT)
├── Market_Scrape/
│   ├── spiders/
│   │   ├── market.py              # 🟢 Daily scrape spider
│   │   ├── market_history.py      # 🔵 Historical backfill spider
│   │   └── market_missing.py      # 🟡 Gap-filler spider
│   └── utils/
│       ├── dates.py               # Date iteration & filename helpers
│       ├── excel.py               # Excel workbook builder & updater
│       ├── paths.py               # Centralized file path definitions
│       ├── sharesansar.py         # Token extraction, AJAX requests, HTML parsing
│       └── storage.py             # CSV save/load & duplicate detection
├── Data/
│   ├── csv/                       # 📂 Daily CSV files (YYYY_MM_DD.csv)
│   └── excel/
│       ├── combined_excel.xlsx    # 📊 Master workbook (one sheet per day)
│       └── list_of_csv_files.txt  # Index of all CSV files
├── scrapy.cfg
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/nepse-market-data.git
cd nepse-market-data

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# 🟢 Scrape today's market data
scrapy crawl market

# 🔵 Backfill all historical data from 2010 to present
scrapy crawl market_history

# 🟡 Fill in any missing dates automatically
scrapy crawl market_missing
```

---

## 🕷️ Spider Comparison

| Spider | When to use | What it does | Excel behavior |
|---|---|---|---|
| `market` | **Daily** (e.g., cron job or GitHub Action) | Fetches today's data, checks for duplicates | Incremental update (fast) |
| `market_history` | **First run / backfill** | Scrapes every date from a start date to an end date, skipping existing files | Full rebuild on completion |
| `market_missing` | **After backfill / maintenance** | Scans existing files, finds earliest date, fetches all gaps up to today | Full rebuild on completion |

---

## 📄 Data Format

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

---

## ⚙️ Configuration

Key settings in `Market_Scrape/settings.py`:

| Setting | Value | Purpose |
|---|---|---|
| `CONCURRENT_REQUESTS_PER_DOMAIN` | 1 | One request at a time per domain |
| `DOWNLOAD_DELAY` | 1 second | Polite delay between requests |
| `ROBOTSTXT_OBEY` | True | Respects robots.txt |

Historical spiders override these for faster backfilling:
- `DOWNLOAD_DELAY`: 0.5s
- `CONCURRENT_REQUESTS`: 4

---

## 🤖 GitHub Actions Automation

A scheduled workflow runs automatically every day at **6:00 PM NPT** (Nepal Time):

1. Checks out the repository
2. Installs Python dependencies
3. Runs `scrapy crawl market` to fetch the day's data
4. Commits and pushes any new/modified CSV and Excel files

You can also trigger it manually from the **Actions** tab in your GitHub repository.

---

## 🧠 How It Works

1. **Token handshake** — Visits ShareSansar's main page, extracts a CSRF token from a hidden input field
2. **AJAX request** — Sends a POST request to the API endpoint with the token, target date, and sector filter
3. **Parse response** — Extracts the HTML table, splits into header + data rows
4. **Save** — Writes to `Data/csv/YYYY_MM_DD.csv`
5. **Excel** — Either rebuilds the full workbook (bulk operations) or appends the latest sheet (daily runs)

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| [Scrapy](https://scrapy.org/) | Web scraping framework |
| [pandas](https://pandas.pydata.org/) | Data manipulation & CSV/Excel I/O |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel file read/write |
| [GitHub Actions](https://github.com/features/actions) | Scheduled daily automation |

---

## 📁 Data Collected

The dataset covers **NEPSE daily trading data from 2010 to present**, with **300–500+ stocks per trading day**. Each day is stored as a separate CSV file and as a named sheet in the master Excel workbook. The data is updated automatically every trading day at 6 PM NPT.

| Metric | Value |
|---|---|
| Date range | 2010 – Present |
| Update frequency | Daily (automated) |
| Stocks per day | 300–500+ |
| File format | CSV (per day) + Excel (master workbook) |
| Total files | One CSV per trading day |

---

## 📝 License

MIT