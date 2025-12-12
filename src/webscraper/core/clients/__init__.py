"""HTTP and browser clients for web scraping."""

from webscraper.core.clients.browser import BrowserClient, BrowserClientError
from webscraper.core.clients.http import HttpClient, HttpClientError

__all__ = [
    "HttpClient",
    "HttpClientError",
    "BrowserClient",
    "BrowserClientError",
]
