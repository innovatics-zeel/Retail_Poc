"""
scheduler.py
Runs the scrape + prediction pipeline on a daily schedule (2 AM ET).
Start with: python scheduler.py
"""
import asyncio
import sys
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, ".")


def run_daily_pipeline():
    logger.info("Scheduler triggered — starting daily scrape")
    try:
        from scrape_runner import run_scrape_plan
        asyncio.run(run_scrape_plan())
        logger.info("Daily scrape completed successfully")

        from predictions.run_predictions import run as run_predictions
        run_predictions()
        logger.info("Daily predictions completed successfully")
    except Exception as e:
        logger.error(f"Daily pipeline failed: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/New_York")

    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_market_intelligence",
        name="Daily marketplace scrape and predictions",
        misfire_grace_time=3600,
        coalesce=True,
    )

    logger.info("Scheduler started — daily scrape + predictions run at 02:00 AM ET")
    logger.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
