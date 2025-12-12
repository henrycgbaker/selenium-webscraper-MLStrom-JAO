# Quick Start Guide

Quickstart for application: JAO Publication Tool

## Prerequisites

- Python 3.9+
- Chrome browser (for Selenium scraper)

## Step 1: Install

```bash
cd webscraper
pip install -e .
```

Or with development tools:
```bash
pip install -e ".[dev]"
```

## Step 2: Run the JAO Scraper

### Option A: API Scraper (Recommended)

The API scraper is faster and more reliable:

```bash
# Download all available data
python -m scripts.jao.api_scraper \
    --start-date 2022-06-08 \
    --end-date 2024-12-31 \
    --output-dir ./data

# Or test with a small date range first
python -m scripts.jao.api_scraper \
    --start-date 2024-01-01 \
    --end-date 2024-01-07 \
    --output-dir ./test_data \
    --verbose
```

### Option B: Selenium Scraper

Use if the API approach doesn't work:

```bash
python -m scripts.jao.scraper \
    --start-date 2024-01-01 \
    --end-date 2024-01-07 \
    --output-dir ./test_data \
    --verbose \
    --headed  # Shows browser window for debugging
```

### Using Make (Optional)

```bash
# Run API scraper with default dates
make jao-api

# Customize dates
make jao-api JAO_START_DATE=2024-01-01 JAO_END_DATE=2024-06-30

# Check progress
make status
```

## Step 3: Monitor Progress

Check status while running (in another terminal):

```bash
webscraper status --state-file ./data/scraper_state.json
```

Output:
```
============================================================
Scraping Session Status
============================================================
Total items: 930
Completed:   450
Failed:      2
In progress: 1
Pending:     477
Success rate: 48.4%
============================================================
```

## Step 4: Handle Failures

If some dates fail:

```bash
# List failed dates
webscraper list-dates --state-file ./data/scraper_state.json --failed-only

# Simply re-run - failed dates will be retried
python -m scripts.jao.api_scraper \
    --start-date 2022-06-08 \
    --end-date 2024-12-31 \
    --output-dir ./data
```

## Options

| Option | Description |
|--------|-------------|
| `--start-date` | Start date (YYYY-MM-DD) |
| `--end-date` | End date (YYYY-MM-DD) |
| `--output-dir` | Where to save files |
| `--rate-limit` | Requests per minute (default: 60) |
| `--verbose` | Show detailed logs |
| `--headless/--headed` | Browser visibility (Selenium only) |
