"""
run_recommendations.py — Orchestrator for the recommendations pipeline.

Flow:
    trend_scores  →  pattern_detector  →  llm_drafter  →  recommendations table

Usage:
    python -m recommendations.run_recommendations
    python recommendations/run_recommendations.py

Run predictions.run_predictions first to populate trend_scores.
"""
from __future__ import annotations
import sys
import time
sys.path.insert(0, ".")

from loguru import logger
from rich.console import Console

console = Console()


def run(category: str | None = None, platform: str | None = None) -> list[dict]:
    console.rule("[bold blue]Recommendations Pipeline")
    t0 = time.time()

    # ── Step 1: Detect patterns ───────────────────────────────────
    console.print("\n[yellow]Step 1:[/yellow] Detecting patterns in trend scores...")
    patterns: list[dict] = []
    try:
        from recommendations.pattern_detector import load_trend_scores, detect_patterns
        df = load_trend_scores()
        if df.empty:
            console.print("  [red]No trend scores found.[/red] Run predictions first:")
            console.print("    python -m predictions.run_predictions")
            return []
        patterns = detect_patterns(df)
        console.print(f"  [green]✓[/green] {len(patterns)} patterns detected")
        for p in patterns[:6]:
            console.print(f"    [{p['pattern_type']}] {p['attr_key']}={p['attr_value']}")
    except Exception as exc:
        console.print(f"  [red]✗[/red] pattern_detector: {exc}")
        logger.exception("pattern_detector failed")
        return []

    if not patterns:
        console.print("  [yellow]No patterns detected — collect more data via the scraper.[/yellow]")
        return []

    # ── Step 2: Draft via configured LLM ──────────────────────────
    console.print(f"\n[yellow]Step 2:[/yellow] Drafting {len(patterns)} recommendations via configured LLM...")
    recommendations: list[dict] = []
    try:
        from recommendations.llm_drafter import draft_all
        recommendations = draft_all(patterns)
        console.print(f"  [green]✓[/green] {len(recommendations)} recommendations drafted")
    except Exception as exc:
        console.print(f"  [red]✗[/red] llm_drafter: {exc}")
        logger.exception("llm_drafter failed")
        return []

    # ── Step 3: Save to DB ────────────────────────────────────────
    console.print("\n[yellow]Step 3:[/yellow] Saving to recommendations table...")
    try:
        from recommendations.recommendation_store import save_recommendations
        saved = save_recommendations(recommendations)
        console.print(f"  [green]✓[/green] {saved} recommendations saved")
    except Exception as exc:
        console.print(f"  [red]✗[/red] recommendation_store: {exc}")
        logger.exception("recommendation_store failed")
        return []

    elapsed = round(time.time() - t0, 1)
    console.rule(f"[bold green]Done in {elapsed}s — {len(recommendations)} recommendations")
    return recommendations


if __name__ == "__main__":
    run()
