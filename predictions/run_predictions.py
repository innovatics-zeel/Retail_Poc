"""
run_predictions.py — Orchestrator: runs all prediction modules in sequence.

Usage:
    python -m predictions.run_predictions
    python predictions/run_predictions.py

Writes results to the trend_scores table.
Run this after ETL (scrape_runner.py) completes.
"""
from __future__ import annotations
import sys
import time
sys.path.insert(0, ".")

from loguru import logger
from rich.console import Console

console = Console()


def run() -> dict:
    console.rule("[bold blue]Predictions Pipeline")
    t0 = time.time()

    # ── Step 1: Trend momentum ────────────────────────────────────
    console.print("\n[yellow]Step 1:[/yellow] Computing trend momentum scores...")
    scores: list = []
    try:
        from predictions.trend_momentum import compute_all as _momentum
        scores = _momentum()
        console.print(f"  [green]✓[/green] {len(scores)} trend scores written to DB")
    except Exception as exc:
        console.print(f"  [red]✗[/red] trend_momentum: {exc}")
        logger.exception("trend_momentum failed")

    # ── Step 2: Review velocity ───────────────────────────────────
    console.print("\n[yellow]Step 2:[/yellow] Computing review velocity forecasts...")
    velocity: list = []
    try:
        from predictions.review_velocity import compute_all as _velocity
        velocity = _velocity()
        console.print(f"  [green]✓[/green] {len(velocity)} category-platform velocity forecasts")
    except Exception as exc:
        console.print(f"  [red]✗[/red] review_velocity: {exc}")
        logger.exception("review_velocity failed")

    # ── Step 3: Rating trends ─────────────────────────────────────
    console.print("\n[yellow]Step 3:[/yellow] Computing rating trends...")
    rating_trends: list = []
    try:
        from predictions.rating_trends import compute_all as _rating
        rating_trends = _rating()
        console.print(f"  [green]✓[/green] {len(rating_trends)} attribute rating trends")
    except Exception as exc:
        console.print(f"  [red]✗[/red] rating_trends: {exc}")
        logger.exception("rating_trends failed")

    # ── Step 4: Explanations ──────────────────────────────────────
    console.print("\n[yellow]Step 4:[/yellow] Generating plain-English explanations...")
    explained = 0
    try:
        from predictions.explainability import generate_all as _explain
        explained = _explain()
        console.print(f"  [green]✓[/green] {explained} explanations written")
    except Exception as exc:
        console.print(f"  [red]✗[/red] explainability: {exc}")
        logger.exception("explainability failed")

    elapsed = round(time.time() - t0, 1)
    console.rule(f"[bold green]Done in {elapsed}s")

    return {
        "scores":        len(scores),
        "velocity":      len(velocity),
        "rating_trends": len(rating_trends),
        "explained":     explained,
    }


if __name__ == "__main__":
    run()
