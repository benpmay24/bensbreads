"""Database-backed lock and timing for Dog Watch sync."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import DogWatchSyncState

logger = logging.getLogger(__name__)

STALE_LOCK_MINUTES = 30


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


def clear_stale_lock() -> bool:
    """
    Release a sync lock left behind by a crashed or interrupted sync.
    Returns True if a stale lock was cleared.
    """
    state = get_sync_state()
    if not state.is_running:
        return False

    progress = state.progress or {}
    if progress.get('running'):
        updated_at = progress.get('updated_at')
        if updated_at:
            updated = parse_datetime(updated_at)
            if updated and timezone.now() - updated < timedelta(minutes=STALE_LOCK_MINUTES):
                return False

    state.is_running = False
    state.progress = {'running': False}
    state.save(update_fields=['is_running', 'progress'])
    logger.warning('Cleared stale Dog Watch sync lock')
    return True


def sync_status_label() -> str:
    """Human-readable sync state for the UI."""
    clear_stale_lock()
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
    clear_stale_lock()
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
