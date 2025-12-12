"""Webscraper - A modular Python framework for date-based web scraping."""

from webscraper.core.config import ScraperConfig
from webscraper.core.state import DownloadStatus, StateManager
from webscraper.core.rate_limiter import AdaptiveRateLimiter, RateLimiter
from webscraper.core.clients.http import HttpClient, HttpClientError
from webscraper.core.clients.browser import BrowserClient, BrowserClientError
from webscraper.scrapers.base import BaseScraper
from webscraper.validation.csv import CSVValidator
from webscraper.exceptions import WebscraperError, ValidationError

__version__ = "0.1.0"

__all__ = [
    # Config
    "ScraperConfig",
    # State
    "DownloadStatus",
    "StateManager",
    # Rate limiting
    "RateLimiter",
    "AdaptiveRateLimiter",
    # Clients
    "HttpClient",
    "HttpClientError",
    "BrowserClient",
    "BrowserClientError",
    # Scrapers
    "BaseScraper",
    # Validation
    "CSVValidator",
    # Exceptions
    "WebscraperError",
    "ValidationError",
]
