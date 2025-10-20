"""Background job scheduler using APScheduler.

Manages scheduled tasks for:
- View count synchronization (every 5 seconds)
- Offer expiration processing (every 1 minute)
- Cache cleanup (daily)
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.background.jobs.sync_view_counts import sync_view_counts_job
from app.background.jobs.process_expired_offers import process_expired_offers_job
from app.background.jobs.cleanup_old_cache import cleanup_old_cache_job

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Manages background scheduled tasks."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._jobs_registered = False

    def register_jobs(self) -> None:
        """Register all background jobs."""
        if self._jobs_registered:
            logger.warning("Jobs already registered, skipping")
            return

        logger.info("Registering background jobs...")

        # Job 1: Sync view counts every 5 seconds
        self.scheduler.add_job(
            sync_view_counts_job,
            trigger=IntervalTrigger(seconds=5),
            id="sync_view_counts",
            name="Sync view counts to database",
            replace_existing=True,
            max_instances=1,
        )

        # Job 2: Process expired offers every 1 minute
        self.scheduler.add_job(
            process_expired_offers_job,
            trigger=IntervalTrigger(minutes=1),
            id="process_expired_offers",
            name="Process expired offers",
            replace_existing=True,
            max_instances=1,
        )

        # Job 3: Cleanup old cache entries daily at 3 AM
        self.scheduler.add_job(
            cleanup_old_cache_job,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup_old_cache",
            name="Cleanup old cache entries",
            replace_existing=True,
            max_instances=1,
        )

        self._jobs_registered = True
        logger.info("Background jobs registered successfully")

    def start(self) -> None:
        """Start the scheduler."""
        if not self._jobs_registered:
            self.register_jobs()

        self.scheduler.start()
        logger.info("Background scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Background scheduler stopped")

    def get_job_status(self) -> dict:
        """Get status of all jobs.

        Returns:
            Dictionary with job information
        """
        jobs = self.scheduler.get_jobs()
        return {
            "running": self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                }
                for job in jobs
            ],
        }


# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Get global scheduler instance.

    Returns:
        BackgroundScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start_scheduler() -> None:
    """Start the global background scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler() -> None:
    """Stop the global background scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
