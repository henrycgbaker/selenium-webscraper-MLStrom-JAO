"""Date range utilities for webscraper."""

from datetime import date
from typing import Iterator

from dateutil.rrule import DAILY, rrule


def generate_date_range(start_date: date, end_date: date) -> list[date]:
    """Generate list of dates in range (inclusive).

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of date objects

    Example:
        >>> from datetime import date
        >>> dates = generate_date_range(date(2024, 1, 1), date(2024, 1, 3))
        >>> [d.isoformat() for d in dates]
        ['2024-01-01', '2024-01-02', '2024-01-03']
    """
    return [d.date() for d in rrule(DAILY, dtstart=start_date, until=end_date)]


def iter_date_range(start_date: date, end_date: date) -> Iterator[date]:
    """Iterate over dates in range (inclusive).

    Memory-efficient alternative to generate_date_range for large ranges.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Yields:
        date objects

    Example:
        >>> from datetime import date
        >>> for d in iter_date_range(date(2024, 1, 1), date(2024, 1, 3)):
        ...     print(d.isoformat())
        2024-01-01
        2024-01-02
        2024-01-03
    """
    for dt in rrule(DAILY, dtstart=start_date, until=end_date):
        yield dt.date()


def format_date(d: date, fmt: str = "%Y-%m-%d") -> str:
    """Format date as string.

    Args:
        d: Date to format
        fmt: Format string (default: ISO format YYYY-MM-DD)

    Returns:
        Formatted date string
    """
    return d.strftime(fmt)


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> date:
    """Parse date from string.

    Args:
        date_str: Date string to parse
        fmt: Format string (default: ISO format YYYY-MM-DD)

    Returns:
        Parsed date object

    Raises:
        ValueError: If date_str doesn't match format
    """
    from datetime import datetime

    return datetime.strptime(date_str, fmt).date()
