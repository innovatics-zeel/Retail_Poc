"""
scheduler.py
Runs the full scrape pipeline on a weekly schedule (every Sunday at 2 AM).
Start with: python scheduler.py
"""
import asyncio
import sys
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, ".")


def run_weekly_scrape():
    logger.info("Scheduler triggered — starting weekly scrape")
    try:
        from scrape_runner import run_scrape_plan
        asyncio.run(run_scrape_plan())
        logger.info("Weekly scrape completed successfully")
    except Exception as e:
        logger.error(f"Weekly scrape failed: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/New_York")

    scheduler.add_job(
        run_weekly_scrape,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_scrape",
        name="Weekly marketplace scrape",
        misfire_grace_time=3600,
        coalesce=True,
    )

    logger.info("Scheduler started — weekly scrape runs every Sunday at 02:00 AM ET")
    logger.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
