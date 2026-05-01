"""
scrape_runner.py
─────────────────────────────────────────────────────────
Main entry point for scraping.
Add any new platform/category combo to SCRAPE_PLAN — no other changes needed.
"""

import asyncio
import sys
from loguru import logger
from rich.console import Console
from rich.table import Table

from scraper.registry import get_scraper
from pipeline.ingest import ingest_batch
from database.connection import test_connection, verify_schema

console = Console()

# ── What to scrape — edit this list to add/remove jobs ───────────────────────
SCRAPE_PLAN = [
    {"platform": "nordstrom", "category": "mens_tshirts",   "max_products": 0},
    {"platform": "nordstrom", "category": "womens_dresses",  "max_products": 0},
    {"platform": "amazon",    "category": "mens_tshirts",   "max_products": 5},
    {"platform": "amazon",    "category": "womens_dresses",  "max_products": 5},
]


async def run_scrape_plan():
    all_results = {}

    for job in SCRAPE_PLAN:
        platform    = job["platform"]
        category    = job["category"]
        max_products = job["max_products"]

        console.print(f"\n[bold cyan]▶ Starting {platform} / {category}...[/]")

        scraper_cls = get_scraper(platform, category)

        async with scraper_cls() as scraper:
            console.print(f"  🛍️ [white]{platform.title()} | {category} | max={max_products}[/]")
            records = await scraper.search_category(category, max_products=max_products)
            summary = ingest_batch(records, category, platform=platform)
            all_results[f"{platform} / {category}"] = summary

    return all_results


async def main():
    console.print("\n[bold cyan]╔═════════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║   INNOVATICS — Program 1 · Scrape Runner    ║[/]")
    console.print("[bold cyan]╚═════════════════════════════════════════════╝[/]\n")

    console.print("[bold]1.[/] Checking local PostgreSQL connection...")
    if not test_connection():
        console.print("\n[bold red]Cannot reach PostgreSQL.[/]")
        console.print("Make sure PostgreSQL is running and your [bold].env[/] is correct.")
        sys.exit(1)

    console.print("[bold]2.[/] Verifying database schema...")
    if not verify_schema():
        console.print("\n[bold red]Database schema does not match current models.[/]")
        console.print("Run migrations first:  python -c \"from database.connection import run_migrations; run_migrations()\"")
        sys.exit(1)

    console.print("[bold]3.[/] Scraping marketplaces...\n")
    results = await run_scrape_plan()

    console.print("\n")
    table = Table(title="Scrape Summary", style="cyan", show_lines=True)
    table.add_column("Job",       style="white", min_width=35)
    table.add_column("Total",     justify="right")
    table.add_column("✅ Saved",  justify="right", style="green")
    table.add_column("❌ Failed", justify="right", style="red")
    table.add_column("⏭ Skipped",justify="right", style="yellow")

    total_saved = 0
    for job, s in results.items():
        table.add_row(job, str(s["total"]), str(s["success"]), str(s["failed"]), str(s["skipped"]))
        total_saved += s["success"]

    console.print(table)
    console.print(f"\n[bold green]✅ {total_saved} records saved to local PostgreSQL[/]")
    console.print("[dim]All records tagged: data_label = 'demonstration_data'[/]\n")


if __name__ == "__main__":
    asyncio.run(main())
