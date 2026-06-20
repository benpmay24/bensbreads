"""Background scheduler for Dog Watch data sync."""
import logging
import os
import sys
import threading
import time

from django.conf import settings
from django.utils import timezone

from main.dog_watch import sync_state

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 900  # 15 minutes


def _should_start_scheduler() -> bool:
    if not getattr(settings, 'DOG_WATCH_SYNC_ENABLED', True):
        return False
    if os.environ.get('DJANGO_SKIP_DOG_WATCH_SCHEDULER', '').lower() == 'true':
        return False
    if len(sys.argv) > 1 and sys.argv[1] in {
        'migrate', 'makemigrations', 'shell', 'test', 'scrape_puppy_mills',
        'send_daily_update_reminder', 'collectstatic',
    }:
        return False
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        return False
    return True


def _run_sync():
    from main.dog_watch.scraper import run_scheduled_sync

    try:
        result = run_scheduled_sync()
        if result.get('skipped'):
            logger.info('Dog Watch sync skipped: %s', result.get('reason'))
        else:
            logger.info(
                'Dog Watch sync finished: enriched=%s mapped=%s',
                result.get('enriched', 0),
                result.get('mapped_count', 0),
            )
    except Exception:
        logger.exception('Dog Watch scheduled sync failed')


def _scheduler_loop():
    logger.info(
        'Dog Watch scheduler started (adaptive interval, checking every %s min)',
        CHECK_INTERVAL_SECONDS // 60,
    )
    while True:
        try:
            if sync_state.is_sync_due():
                _run_sync()
        except Exception:
            logger.exception('Dog Watch scheduler loop error')
        time.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler():
    if not _should_start_scheduler():
        return
    sync_state.clear_orphaned_lock_on_startup()
    thread = threading.Thread(target=_scheduler_loop, daemon=True, name='dog-watch-scheduler')
    thread.start()
