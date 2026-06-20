"""Database-backed lock and timing for Dog Watch sync."""
import logging
import os
import sys
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import DogWatchSyncState

logger = logging.getLogger(__name__)

STALE_LOCK_MINUTES = 2


def get_sync_state() -> DogWatchSyncState:
    return DogWatchSyncState.load()


def get_last_sync_summary() -> dict:
    state = get_sync_state()
    summary = dict(state.last_summary or {})
    if state.last_sync_at:
        summary.setdefault('completed_at', state.last_sync_at.isoformat())
    return summary


def sync_interval_hours() -> float:
    return float(getattr(settings, 'DOG_WATCH_SYNC_INTERVAL_HOURS', 24))


def next_sync_at():
    """When the next automatic sync is scheduled."""
    state = get_sync_state()
    if not state.last_sync_at:
        return timezone.now()
    return state.last_sync_at + timedelta(hours=sync_interval_hours())


def hours_since_last_sync() -> float | None:
    state = get_sync_state()
    if not state.last_sync_at:
        return None
    return (timezone.now() - state.last_sync_at).total_seconds() / 3600


def is_sync_due() -> bool:
    hours_since = hours_since_last_sync()
    if hours_since is None:
        return True
    return hours_since >= sync_interval_hours()


def get_progress() -> dict:
    state = get_sync_state()
    return state.progress or {'running': False}


def current_worker_pid() -> int:
    return os.getpid()


def is_process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    return True


def has_pending_resume() -> bool:
    progress = get_progress()
    return bool(progress.get('resume_from')) or progress.get('resume_phase') == 'geocode'


def _progress_after_clear(progress: dict) -> dict:
    cleared: dict = {'running': False}
    phase = progress.get('phase', '')
    current = int(progress.get('current') or 0)
    if phase == 'geocode' and current > 0:
        cleared['resume_phase'] = 'geocode'
        cleared['resume_from'] = current
    elif phase == 'check' and current > 0:
        cleared['resume_from'] = current
    return cleared


def _heartbeat_is_fresh(progress: dict) -> bool:
    updated_at = progress.get('updated_at')
    if not updated_at:
        return False
    updated = parse_datetime(updated_at)
    if not updated:
        return False
    return timezone.now() - updated < timedelta(minutes=STALE_LOCK_MINUTES)


def _sync_lock_is_active(progress: dict) -> bool:
    """True when another live worker is actively syncing."""
    worker_pid = progress.get('worker_pid')
    if worker_pid and worker_pid != current_worker_pid():
        if is_process_alive(worker_pid) and _heartbeat_is_fresh(progress):
            return True
        return False
    if worker_pid == current_worker_pid():
        return _heartbeat_is_fresh(progress)
    return _heartbeat_is_fresh(progress)


def recover_sync_lock(force: bool = False) -> bool:
    """
    Release a sync lock held by a dead worker or with a stale heartbeat.
    Preserves resume_from so interrupted syncs can continue.
    """
    state = get_sync_state()
    if not state.is_running:
        return False

    progress = state.progress or {}
    if not force and _sync_lock_is_active(progress):
        return False

    state.is_running = False
    state.progress = _progress_after_clear(progress)
    state.save(update_fields=['is_running', 'progress'])
    logger.warning(
        'Recovered Dog Watch sync lock (worker_pid=%s, phase=%s, current=%s)',
        progress.get('worker_pid'),
        progress.get('phase'),
        progress.get('current'),
    )
    return True


def clear_stale_lock() -> bool:
    """Backward-compatible alias for recover_sync_lock."""
    return recover_sync_lock()


def clear_orphaned_lock_on_startup() -> bool:
    """Clear a lock left by a previous process after deploy or restart."""
    state = get_sync_state()
    if not state.is_running:
        return False

    progress = state.progress or {}
    worker_pid = progress.get('worker_pid')
    if worker_pid == current_worker_pid() and _heartbeat_is_fresh(progress):
        return False

    if worker_pid and worker_pid != current_worker_pid() and is_process_alive(worker_pid):
        if _heartbeat_is_fresh(progress):
            return False

    return recover_sync_lock(force=True)


def _should_auto_resume_on_startup() -> bool:
    if os.environ.get('DJANGO_SKIP_DOG_WATCH_SCHEDULER', '').lower() == 'true':
        return False
    if len(sys.argv) > 1 and sys.argv[1] in {
        'migrate', 'makemigrations', 'shell', 'test', 'collectstatic',
        'dog_watch_recover_sync',
    }:
        return False
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        return False
    return True


def _auto_resume_sync() -> None:
    time.sleep(1)
    from main.dog_watch.scraper import run_full_sync

    try:
        result = run_full_sync(force=True)
        if result.get('skipped'):
            logger.info('Dog Watch auto-resume skipped: %s', result.get('reason'))
        else:
            logger.info('Dog Watch auto-resume finished: %s', result.get('status'))
    except Exception:
        logger.exception('Dog Watch auto-resume failed')


def recover_on_startup(auto_resume: bool = True) -> None:
    """
    Called on process start: clear locks from dead workers and optionally
    resume an interrupted sync (e.g. after a production deploy).
    """
    cleared = clear_orphaned_lock_on_startup()
    if not auto_resume or not _should_auto_resume_on_startup():
        return
    if cleared or has_pending_resume():
        thread = threading.Thread(
            target=_auto_resume_sync,
            daemon=True,
            name='dog-watch-auto-resume',
        )
        thread.start()
        logger.info('Scheduled Dog Watch sync auto-resume after recovery')


def sync_status_label() -> str:
    """Human-readable sync state for the UI."""
    recover_sync_lock()
    state = get_sync_state()
    progress = get_progress()

    if progress.get('running') or state.is_running:
        return 'syncing'
    if not state.last_sync_at:
        return 'never_synced'
    if is_sync_due():
        return 'due'
    return 'up_to_date'


def try_acquire_lock() -> DogWatchSyncState | None:
    recover_sync_lock()
    DogWatchSyncState.load()
    with transaction.atomic():
        state = DogWatchSyncState.objects.select_for_update().get(pk=1)
        if state.is_running:
            return None
        state.is_running = True
        state.progress = {
            'running': True,
            'phase': 'scheduled',
            'current': 0,
            'total': 0,
            'message': 'Starting full Dog Watch update...',
            'worker_pid': current_worker_pid(),
            'updated_at': timezone.now().isoformat(),
        }
        state.save(update_fields=['is_running', 'progress'])
        return state


def release_lock(state: DogWatchSyncState, summary: dict) -> None:
    state.is_running = False
    state.last_sync_at = timezone.now()
    state.last_summary = summary
    state.progress = {'running': False}
    state.save(update_fields=['is_running', 'last_sync_at', 'last_summary', 'progress'])


def aphis_delay() -> float:
    return getattr(settings, 'DOG_WATCH_APHIS_DELAY_SECONDS', 1.5)
