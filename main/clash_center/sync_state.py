"""Lock and timing for Clash Center sync (cron job only)."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import ClashCenterSyncState

logger = logging.getLogger(__name__)

STALE_LOCK_MINUTES = 15


def get_sync_state() -> ClashCenterSyncState:
    return ClashCenterSyncState.load()


def get_last_sync_summary() -> dict:
    state = get_sync_state()
    summary = dict(state.last_summary or {})
    if state.last_sync_at:
        summary.setdefault('completed_at', state.last_sync_at.isoformat())
    return summary


def sync_interval_hours() -> float:
    return float(getattr(settings, 'CLASH_CENTER_SYNC_INTERVAL_HOURS', 1))


def is_sync_due() -> bool:
    state = get_sync_state()
    if not state.last_sync_at:
        return True
    return timezone.now() - state.last_sync_at >= timedelta(hours=sync_interval_hours())


def next_sync_at():
    state = get_sync_state()
    if not state.last_sync_at:
        return timezone.now()
    return state.last_sync_at + timedelta(hours=sync_interval_hours())


def clear_stale_lock() -> None:
    state = get_sync_state()
    if not state.is_running:
        return
    progress = state.progress or {}
    updated_at = progress.get('updated_at')
    if updated_at:
        updated = parse_datetime(updated_at)
        if updated and timezone.now() - updated < timedelta(minutes=STALE_LOCK_MINUTES):
            return
    state.is_running = False
    state.progress = {'running': False}
    state.save(update_fields=['is_running', 'progress'])
    logger.warning('Cleared stale Clash Center sync lock')


def force_clear_lock() -> None:
    state = get_sync_state()
    state.is_running = False
    state.progress = {'running': False}
    state.save(update_fields=['is_running', 'progress'])
    logger.warning('Force-cleared Clash Center sync lock')


def normalize_progress(state: ClashCenterSyncState) -> dict:
    progress = dict(state.progress or {})
    if state.is_running:
        progress['running'] = True
        return progress
    if progress.get('running'):
        cleared = {'running': False}
        state.progress = cleared
        state.save(update_fields=['progress'])
        return cleared
    return progress


def set_progress(message: str, current: int = 0, total: int = 0) -> None:
    state = get_sync_state()
    state.progress = {
        'running': True,
        'current': current,
        'total': total,
        'message': message,
        'updated_at': timezone.now().isoformat(),
    }
    state.save(update_fields=['progress'])


def try_acquire_lock() -> ClashCenterSyncState | None:
    clear_stale_lock()
    with transaction.atomic():
        state = ClashCenterSyncState.objects.select_for_update().get(pk=1)
        if state.is_running:
            return None
        state.is_running = True
        state.progress = {
            'running': True,
            'current': 0,
            'total': 0,
            'message': 'Starting…',
            'updated_at': timezone.now().isoformat(),
        }
        state.save(update_fields=['is_running', 'progress'])
        return state


def release_lock(state: ClashCenterSyncState, summary: dict) -> None:
    state.is_running = False
    state.last_sync_at = timezone.now()
    state.last_summary = summary
    state.progress = {'running': False}
    state.save(update_fields=['is_running', 'last_sync_at', 'last_summary', 'progress'])


def sync_status_label() -> str:
    clear_stale_lock()
    state = get_sync_state()
    if state.is_running:
        return 'syncing'
    if not state.last_sync_at:
        return 'never_synced'
    if is_sync_due():
        return 'due'
    return 'up_to_date'


def refresh_collection_status() -> tuple[bool, dict]:
    clear_stale_lock()
    state = get_sync_state()
    progress = normalize_progress(state)
    return state.is_running, progress
