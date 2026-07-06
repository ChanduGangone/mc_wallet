import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.core.exchange_rates import fetch_and_store_snapshot

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    scheduler.add_job(
        fetch_and_store_snapshot,
        trigger=CronTrigger(hour=settings.exchange_rate_refresh_hour_utc, minute=0),
        id="daily_exchange_rate_refresh",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started; daily exchange rate refresh at %02d:00 UTC", settings.exchange_rate_refresh_hour_utc)


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
