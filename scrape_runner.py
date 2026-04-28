"""
scrape_runner.py
─────────────────────────────────────────────────────────
Main entry point for scraping.

BEFORE RUNNING:
  1. Install PostgreSQL locally + open pgAdmin
  2. Create database:  innovatics_p1
  3. Copy .env.example → .env, fill in your DB_USER + DB_PASSWORD
  4. pip install -r requirements.txt
  5. playwright install chromium
  6. python scrape_runner.py

What it does:
  • Scrapes Amazon US  — Men's T-shirts + Women's Casual Dresses
  • Scrapes Nordstrom  — same two categories
  • Validates every record with Pydantic
  • Upserts into local PostgreSQL (4 tables)
"""
import asyncio
import sys
from loguru import logger
from rich.console import Console
from rich.table import Table

from scraper.nordstrom_scraper import NordstromScraper
from pipeline.ingest import ingest_batch
from database.connection import test_connection, verify_schema

console = Console()

# ── What to scrape ────────────────────────────────────────────
# Amazon + Women's dresses will be added in the next phase
SCRAPE_PLAN = [
    {"platform": "nordstrom", "category": "mens_tshirts", "max_products": 100},
]


async def run_scrape_plan():
    all_results = {}

    nordstrom_jobs = [j for j in SCRAPE_PLAN if j["platform"] == "nordstrom"]
    if nordstrom_jobs:
        console.print("\n[bold cyan]▶ Starting Nordstrom scraper...[/]")
        async with NordstromScraper() as scraper:
            for job in nordstrom_jobs:
                cat = job["category"]
                console.print(f"  👗 [white]Nordstrom | {cat} | max={job['max_products']}[/]")
                records = await scraper.search_category(cat, max_products=job["max_products"])
                summary = ingest_batch(records, cat)
                all_results[f"nordstrom / {cat}"] = summary

    return all_results


async def main():
    console.print("\n[bold cyan]╔═════════════════════════════════════════════╗[/]")
    console.print("[bold cyan]║   INNOVATICS — Program 1 · Scrape Runner    ║[/]")
    console.print("[bold cyan]╚═════════════════════════════════════════════╝[/]\n")

    # Step 1 — DB connection check
    console.print("[bold]1.[/] Checking local PostgreSQL connection...")
    if not test_connection():
        console.print("\n[bold red]Cannot reach PostgreSQL.[/]")
        console.print("Make sure PostgreSQL is running locally and your [bold].env[/] is correct:")
        console.print("  DB_HOST=localhost  DB_PORT=5432")
        console.print("  DB_NAME=Innovatics_Retail  DB_USER=...  DB_PASSWORD=...")
        sys.exit(1)

    # Step 2 — Schema validation
    console.print("[bold]2.[/] Verifying database schema...")
    if not verify_schema():
        console.print("\n[bold red]Database schema does not match the current models.[/]")
        console.print("Run your Alembic/manual migration first, then start the scraper again.")
        sys.exit(1)

    # Step 3 — Scrape
    console.print("[bold]3.[/] Scraping marketplaces...\n")
    results = await run_scrape_plan()

    # Step 4 — Summary
    console.print("\n")
    table = Table(title="Scrape Summary", style="cyan", show_lines=True)
    table.add_column("Job",        style="white",  min_width=35)
    table.add_column("Total",      justify="right")
    table.add_column("✅ Saved",   justify="right", style="green")
    table.add_column("❌ Failed",  justify="right", style="red")
    table.add_column("⏭ Skipped", justify="right", style="yellow")

    total_saved = 0
    for job, s in results.items():
        table.add_row(job, str(s["total"]), str(s["success"]), str(s["failed"]), str(s["skipped"]))
        total_saved += s["success"]

    console.print(table)
    console.print(f"\n[bold green]✅ {total_saved} records saved to local PostgreSQL (innovatics_p1)[/]")
    console.print("[dim]All records tagged: data_label = 'demonstration_data'[/]\n")


if __name__ == "__main__":
    asyncio.run(main())
