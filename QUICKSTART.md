# Quick Start Guide - Lightweight web scraper for Jao Publication Tool

*NB: v1 - this is a quick tool I created for Hertie's Data Science Lab ML Strom project. I briefly worked on extending it out to a generic scraping tool (see [`README`](/Users/henrybaker/Repositories/jao_scraper/README.md)), but this is not fully developed currently (26.11.2025, v1)*

## Prerequisites

- Python 3.8 or higher
- Chrome or Firefox browser installed

## Step 1: Install Dependencies

```bash
cd jao_scraper
pip install -r requirements.txt
```

## Step 2: Configure the Scraper (IMPORTANT!)

Before you can download data, you need to discover either the API endpoint or the page element selectors.

### Option A: Find the API Endpoint (Recommended where possible, but doesn't work for `https://publicationtool.jao.eu/core/maxNetPos`)

1. Open Chrome and navigate to site (here: https://publicationtool.jao.eu/core/maxNetPos)

2. Open Chrome DevTools:
   - Press F12, or
   - Right-click → Inspect

3. Click on the "Network" tab in DevTools > filter by "Fetch/XHR"

4. On the page, locate buttons in the workflow (here: download > date pickers > CSV)

5. Look for new requests in the Network tab:
   - Find requests to `/core/api` or similar
   - Click on the request to see details

6. Note the following information:
   - **Request URL**
   - **Request Method**: GET or POST
   - **Query Parameters** or **Request Payload**: The format of the date parameters

7. Open `scrapers/jao_scraper.py` and update:

```python
# Line 28: Set USE_API to True
USE_API = True

# Line 26: Update the API endpoint
API_ENDPOINT = "/api/data/maxNetPos"  # Replace with actual endpoint

# Lines 79-87: Update the _download_via_api method
def _download_via_api(self, target_date: date) -> Path:
    date_str = target_date.strftime("%Y-%m-%d")

    # Update based on what you saw in DevTools:
    params = {
        "date": date_str,  # Adjust parameter names
        "format": "csv"    # Add any other required parameters
    }

    # ... rest of method
```

### Option B: Find Page Element Selectors (Fallback - but works for our page)

If the API approach doesn't work, you can use Selenium to automate the browser:

1. Open Chrome and navigate to site (here: https://publicationtool.jao.eu/core/maxNetPos)

2. Open Chrome DevTools (F12 / right-click inspect) > Click the "Elements" tab

3. On the page, locate buttons in the workflow (here: download > date pickers > CSV)
   - Right-click → Inspect
   - Note elements' selector (ID, class, or CSS selector)

6. Open `scrapers/jao_scraper.py` and update:

```python
# Lines 30-35: Update the SELECTORS dictionary
    SELECTORS = {
        "download_button": "button.pageButton_rpP4hV2OM0",  # Main download button
        "from_datetime_input": "input.inputBorder",  # From datetime (first one in popup)
        "to_datetime_input": "input.inputBorder",  # To datetime (second one in popup)
        "csv_button": "button.popupButton_GRkGEahdXf",  # CSV button in popup
    }

# Lines 120-150: Update the _download_via_selenium method
# Uncomment and modify the interaction code based on your selectors
```

## Step 3: Test with a Small Date Range

Before downloading ~930 days of data, test with just 2-3 days:

```bash
python main.py jao \
  --start-date 2024-01-01 \
  --end-date 2024-01-03 \
  --output-dir ./test_data \
  --verbose \
  --headed
```

This will:
- Download data for 3 days only
- Show you the browser window (`--headed`)
- Print detailed logs (`--verbose`)
- Save files to `./test_data`

Check that:
- Files are downloaded successfully
- Files contain valid data (run `/tests/validate_csv.py`)

## Step 4: Run the Full Download

Once testing is successful, download all the data:

```bash
python main.py jao \
  --start-date 2022-06-08 \
  --end-date 2024-12-31 \
  --output-dir ./jao_data \
  --rate-limit 60 \
  --verbose
```

This will:
- Download ~930 files (one per day)
- Take 15-90 minutes depending on method (API vs Selenium)
- Save files to `./jao_data/`
- Create a state file for resume capability
- Show progress bar and statistics

## Step 5: Monitor Progress

In another terminal, check the status:

```bash
python main.py status -s ./jao_data/scraper_state.json
```

If the script is interrupted, simply re-run the command from Step 4. It will automatically resume from where it left off.

## Step 6: Handle Failures

If some dates fail to download:

1. Check which dates failed:
```bash
python main.py list-dates -s ./jao_data/scraper_state.json --failed-only
```

2. Check the log file (if you specified `--log-file`)

3. The scraper will automatically retry failed dates up to 3 times

## Troubleshooting

### Issue: "Driver not started" error

**Solution**: The Selenium client failed to start. Try:
```bash
# Use Firefox instead
python main.py jao ... --browser firefox

# Or update Chrome to latest version
```

### Issue: "Element not found" error

**Solution**: The page structure changed or selectors are wrong. Repeat Step 2 to find correct selectors.

### Issue: Rate limiting (429 errors)

**Solution**: Reduce the rate limit:
```bash
python main.py jao ... --rate-limit 30
```

## Advanced Usage

### Resume from a Failed Run

If the scraper crashes or you stop it, just run the same command again:

```bash
python main.py jao \
  --start-date 2022-06-08 \
  --end-date 2024-12-31 \
  --output-dir ./jao_data \
  --resume
```

The `--resume` flag (default) will skip already completed dates.

### Reset and Start Over

To clear all progress and start fresh:

```bash
python main.py reset -s ./jao_data/scraper_state.json
```

### Run Without Validation (Faster)

To skip CSV validation (not recommended):

```bash
python main.py jao ... --no-validate
```

### Save Detailed Logs

To save all logs to a file for debugging:

```bash
python main.py jao ... --log-file ./scraper.log --verbose
```
