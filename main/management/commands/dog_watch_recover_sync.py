from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recover a stuck Dog Watch sync after deploy and optionally resume it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-only',
            action='store_true',
            help='Clear the lock without starting a new sync',
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume the interrupted sync after clearing the lock',
        )

    def handle(self, *args, **options):
        from main.dog_watch.scraper import get_progress, run_full_sync
        from main.dog_watch.sync_state import (
            clear_orphaned_lock_on_startup,
            get_sync_state,
            has_pending_resume,
            recover_sync_lock,
        )

        cleared = clear_orphaned_lock_on_startup() or recover_sync_lock(force=True)
        progress = get_progress()
        state = get_sync_state()

        if cleared:
            self.stdout.write(self.style.SUCCESS('Cleared stuck Dog Watch sync lock.'))
        else:
            self.stdout.write('No active sync lock to clear.')

        self.stdout.write(f'  is_running={state.is_running}')
        self.stdout.write(f'  resume_from={progress.get("resume_from", "—")}')
        self.stdout.write(f'  resume_phase={progress.get("resume_phase", "—")}')

        if options['clear_only']:
            return

        if options['resume'] or has_pending_resume():
            self.stdout.write('Starting resumed sync...')
            summary = run_full_sync(force=True)
            if summary.get('skipped'):
                self.stdout.write(self.style.WARNING(
                    f"Skipped: {summary.get('reason', 'unknown')}"
                ))
                return
            self.stdout.write(self.style.SUCCESS(
                f"Sync finished: {summary.get('status')} "
                f"(checked={summary.get('checked', 0)}, resumed={summary.get('resumed')})"
            ))
