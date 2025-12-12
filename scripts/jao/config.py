"""JAO-specific configuration."""

from datetime import date

# JAO API Configuration
JAO_API_URL = "https://publicationtool.jao.eu/core/api/data/maxNetPos"
JAO_PAGE_URL = "https://publicationtool.jao.eu/core/maxNetPos"
JAO_BASE_URL = "https://publicationtool.jao.eu/core"

# Default date range (data availability)
DEFAULT_START_DATE = date(2022, 6, 8)
DEFAULT_END_DATE = date(2024, 12, 31)

# Selenium Selectors for JAO maxNetPos page
JAO_SELECTORS = {
    "download_button": "button.pageButton_rpP4hV2OM0",
    "from_datetime_input": "input.inputBorder",
    "to_datetime_input": "input.inputBorder",
    "csv_button": "button.popupButton_GRkGEahdXf",
}

# Rate limiting (JAO limit is 100 req/min, we use conservative 60)
DEFAULT_REQUESTS_PER_MINUTE = 60
