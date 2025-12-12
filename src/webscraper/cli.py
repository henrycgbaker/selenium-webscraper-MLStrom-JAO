"""CLI interface for webscraper framework using Typer."""

from pathlib import Path

import typer

app = typer.Typer(
    name="webscraper",
    help="A modular Python framework for date-based web scraping.",
    add_completion=False,
)


@app.command()
def status(
    state_file: Path = typer.Option(
        ...,
        "--state-file",
        "-s",
        help="Path to state file",
        exists=True,
        dir_okay=False,
    ),
) -> None:
    """Show status of a scraping session."""
    from webscraper.core.state import StateManager

    state = StateManager(state_file)
    summary = state.get_summary()

    typer.echo("=" * 60)
    typer.echo("Scraping Session Status")
    typer.echo("=" * 60)
    typer.echo(f"State file: {state_file}")
    typer.echo(f"Created: {state.state.get('created_at', 'N/A')}")
    typer.echo(f"Last updated: {state.state.get('last_updated', 'N/A')}")
    typer.echo("")
    typer.echo(f"Total items: {summary['total']}")
    typer.echo(f"Completed:   {summary['completed']}")
    typer.echo(f"Failed:      {summary['failed']}")
    typer.echo(f"In progress: {summary['in_progress']}")
    typer.echo(f"Pending:     {summary['pending']}")
    typer.echo(f"Success rate: {summary['success_rate']:.1f}%")
    typer.echo("=" * 60)

    # Show failed dates if any
    failed_dates = state.get_failed_dates()
    if failed_dates:
        typer.echo("\nFailed dates:")
        for date_str in sorted(failed_dates)[:10]:
            info = state.state["downloads"][date_str]
            error = info.get("error", "Unknown error")
            typer.echo(f"  {date_str}: {error}")
        if len(failed_dates) > 10:
            typer.echo(f"  ... and {len(failed_dates) - 10} more")


@app.command("list-dates")
def list_dates(
    state_file: Path = typer.Option(
        ...,
        "--state-file",
        "-s",
        help="Path to state file",
        exists=True,
        dir_okay=False,
    ),
    failed_only: bool = typer.Option(
        False,
        "--failed-only",
        help="List only failed dates",
    ),
) -> None:
    """List all dates in a scraping session."""
    from webscraper.core.state import DownloadStatus, StateManager

    state = StateManager(state_file)

    if failed_only:
        dates = state.get_failed_dates()
        typer.echo(f"Failed dates ({len(dates)}):")
    else:
        dates = set(state.state["downloads"].keys())
        typer.echo(f"All dates ({len(dates)}):")

    for date_str in sorted(dates):
        info = state.state["downloads"][date_str]
        status_val = info["status"]
        if failed_only or status_val == DownloadStatus.FAILED.value:
            error = info.get("error", "")
            typer.echo(f"  {date_str}: {status_val} - {error}")
        else:
            typer.echo(f"  {date_str}: {status_val}")


@app.command()
def reset(
    state_file: Path = typer.Option(
        ...,
        "--state-file",
        "-s",
        help="Path to state file",
        exists=True,
        dir_okay=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Reset state file (clear all progress)."""
    from webscraper.core.state import StateManager

    if not force:
        confirm = typer.confirm("Are you sure you want to reset the state?")
        if not confirm:
            raise typer.Abort()

    state = StateManager(state_file)
    state.reset()
    typer.echo(f"State file reset: {state_file}")


@app.command()
def version() -> None:
    """Show version information."""
    from webscraper import __version__

    typer.echo(f"webscraper version {__version__}")


def main() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
