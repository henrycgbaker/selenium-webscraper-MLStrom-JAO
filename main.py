"""CLI interface for web scraper framework."""
import click
from datetime import datetime
from pathlib import Path

from config import ScraperConfig
from scrapers.jao_scraper import JAOScraper


@click.group()
def cli():
    """Web scraping framework for date-based downloads."""
    pass


@cli.command()
@click.option(
    "--start-date",
    "-s",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    "-e",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date (YYYY-MM-DD)",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default="./data",
    help="Output directory for downloaded files",
)
@click.option(
    "--resume/--no-resume",
    default=True,
    help="Resume from previous run (skip completed downloads)",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Validate downloaded files",
)
@click.option(
    "--verbose/--quiet",
    "-v/-q",
    default=False,
    help="Verbose output",
)
@click.option(
    "--headless/--headed",
    default=True,
    help="Run browser in headless mode (for Selenium)",
)
@click.option(
    "--browser",
    type=click.Choice(["chrome", "firefox"]),
    default="chrome",
    help="Browser to use for Selenium",
)
@click.option(
    "--rate-limit",
    type=int,
    default=60,
    help="Maximum requests per minute",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to log file (optional)",
)
def jao(
    start_date,
    end_date,
    output_dir,
    resume,
    validate,
    verbose,
    headless,
    browser,
    rate_limit,
    log_file,
):
    """Download JAO Publication Tool maxNetPos data.

    Example:
        webscraper jao -s 2022-06-08 -e 2024-12-31 -o ./jao_data
    """
    click.echo("=" * 60)
    click.echo("JAO MaxNetPos Data Scraper")
    click.echo("=" * 60)
    click.echo(f"Date range: {start_date.date()} to {end_date.date()}")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Resume: {resume}")
    click.echo(f"Validate: {validate}")
    click.echo(f"Rate limit: {rate_limit} requests/minute")
    click.echo("")

    # Create configuration
    config = ScraperConfig(
        output_dir=output_dir,
        requests_per_minute=rate_limit,
        validate_downloads=validate,
        verbose=verbose,
        headless=headless,
        browser=browser,
        log_file=log_file,
    )

    # Create and run scraper
    with JAOScraper(config) as scraper:
        scraper.run(
            start_date=start_date.date(),
            end_date=end_date.date(),
            resume=resume,
        )

    click.echo("\nDone!")


@cli.command()
@click.option(
    "--state-file",
    "-s",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to state file",
)
def status(state_file):
    """Show status of a scraping session.

    Example:
        webscraper status -s ./data/scraper_state.json
    """
    from utils.state import StateManager

    state = StateManager(state_file)
    summary = state.get_summary()

    click.echo("=" * 60)
    click.echo("Scraping Session Status")
    click.echo("=" * 60)
    click.echo(f"State file: {state_file}")
    click.echo(f"Created: {state.state.get('created_at', 'N/A')}")
    click.echo(f"Last updated: {state.state.get('last_updated', 'N/A')}")
    click.echo("")
    click.echo(f"Total items: {summary['total']}")
    click.echo(f"Completed:   {summary['completed']}")
    click.echo(f"Failed:      {summary['failed']}")
    click.echo(f"In progress: {summary['in_progress']}")
    click.echo(f"Pending:     {summary['pending']}")
    click.echo(f"Success rate: {summary['success_rate']:.1f}%")
    click.echo("=" * 60)

    # Show failed dates if any
    failed_dates = state.get_failed_dates()
    if failed_dates:
        click.echo("\nFailed dates:")
        for date_str in sorted(failed_dates)[:10]:  # Show first 10
            info = state.state["downloads"][date_str]
            error = info.get("error", "Unknown error")
            click.echo(f"  {date_str}: {error}")
        if len(failed_dates) > 10:
            click.echo(f"  ... and {len(failed_dates) - 10} more")


@cli.command()
@click.option(
    "--state-file",
    "-s",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to state file",
)
@click.option(
    "--failed-only",
    is_flag=True,
    help="List only failed dates",
)
def list_dates(state_file, failed_only):
    """List all dates in a scraping session.

    Example:
        webscraper list-dates -s ./data/scraper_state.json --failed-only
    """
    from utils.state import StateManager, DownloadStatus

    state = StateManager(state_file)

    if failed_only:
        dates = state.get_failed_dates()
        click.echo(f"Failed dates ({len(dates)}):")
    else:
        dates = state.state["downloads"].keys()
        click.echo(f"All dates ({len(dates)}):")

    for date_str in sorted(dates):
        info = state.state["downloads"][date_str]
        status = info["status"]
        if failed_only or status == DownloadStatus.FAILED.value:
            error = info.get("error", "")
            click.echo(f"  {date_str}: {status} - {error}")
        else:
            click.echo(f"  {date_str}: {status}")


@cli.command()
@click.option(
    "--state-file",
    "-s",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to state file",
)
@click.confirmation_option(prompt="Are you sure you want to reset the state?")
def reset(state_file):
    """Reset state file (clear all progress).

    Example:
        webscraper reset -s ./data/scraper_state.json
    """
    from utils.state import StateManager

    state = StateManager(state_file)
    state.reset()
    click.echo(f"State file reset: {state_file}")


if __name__ == "__main__":
    cli()
