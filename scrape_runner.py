"""
scrape_runner.py
─────────────────────────────────────────────────────────
Main entry point for scraping.
"""

import asyncio
import sys
from loguru import logger
from rich.console import Console
from rich.table import Table

from scraper.nordstrom_scraper import NordstromScraper
from scraper.nordstrom_womens_dress_scraper import NordstromWomensDressScraper

from pipeline.ingest import ingest_batch
from database.connection import test_connection, verify_schema

console = Console()

# ── What to scrape ────────────────────────────────────────────
SCRAPE_PLAN = [
    {"platform": "nordstrom", "category": "mens_tshirts", "max_products": 1},
    {"platform": "nordstrom", "category": "womens_dresses", "max_products": 1},
]


def get_scraper_class(platform: str, category: str):
    if platform == "nordstrom" and category == "mens_tshirts":
        return NordstromScraper

    if platform == "nordstrom" and category == "womens_dresses":
        return NordstromWomensDressScraper

    raise ValueError(f"Unsupported scrape job: {platform} / {category}")


async def run_scrape_plan():
    all_results = {}

    for job in SCRAPE_PLAN:
        platform = job["platform"]
        category = job["category"]
        max_products = job["max_products"]

        console.print(f"\n[bold cyan]▶ Starting {platform} scraper for {category}...[/]")

        scraper_cls = get_scraper_class(platform, category)

        async with scraper_cls() as scraper:
            console.print(
                f"  🛍️ [white]{platform.title()} | {category} | max={max_products}[/]"
            )

            records = await scraper.search_category(
                category,
                max_products=max_products,
            )

            summary = ingest_batch(records, category)
            all_results[f"{platform} / {category}"] = summary

    return all_results


async def main():
    console.print("\n[bold cyan]╔═════════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║   INNOVATICS — Program 1 · Scrape Runner    ║[/]")
    console.print("[bold cyan]╚═════════════════════════════════════════════╝[/]\n")

    console.print("[bold]1.[/] Checking local PostgreSQL connection...")
    if not test_connection():
        console.print("\n[bold red]Cannot reach PostgreSQL.[/]")
        console.print("Make sure PostgreSQL is running locally and your [bold].env[/] is correct:")
        console.print("  DB_HOST=localhost  DB_PORT=5432")
        console.print("  DB_NAME=Innovatics_Retail  DB_USER=...  DB_PASSWORD=...")
        sys.exit(1)

    console.print("[bold]2.[/] Verifying database schema...")
    if not verify_schema():
        console.print("\n[bold red]Database schema does not match the current models.[/]")
        console.print("Run your Alembic/manual migration first, then start the scraper again.")
        sys.exit(1)

    console.print("[bold]3.[/] Scraping marketplaces...\n")
    results = await run_scrape_plan()

    console.print("\n")

    table = Table(title="Scrape Summary", style="cyan", show_lines=True)
    table.add_column("Job", style="white", min_width=35)
    table.add_column("Total", justify="right")
    table.add_column("✅ Saved", justify="right", style="green")
    table.add_column("❌ Failed", justify="right", style="red")
    table.add_column("⏭ Skipped", justify="right", style="yellow")

    total_saved = 0

    for job, s in results.items():
        table.add_row(
            job,
            str(s["total"]),
            str(s["success"]),
            str(s["failed"]),
            str(s["skipped"]),
        )
        total_saved += s["success"]

    console.print(table)
    console.print(f"\n[bold green]✅ {total_saved} records saved to local PostgreSQL[/]")
    console.print("[dim]All records tagged: data_label = 'demonstration_data'[/]\n")


if __name__ == "__main__":
    asyncio.run(main())