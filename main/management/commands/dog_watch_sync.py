from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Check all dog breeders for new APHIS inspection reports (runs every 24h)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-check every breeder even if checked within the last 24 hours',
        )
        parser.add_argument(
            '--clear-lock',
            action='store_true',
            help='Clear a stuck sync lock before running',
        )

    def handle(self, *args, **options):
        from main.dog_watch.scraper import check_for_new_reports
        from main.dog_watch.sync_state import force_clear_lock, get_progress

        if options['clear_lock']:
            force_clear_lock()
            self.stdout.write(self.style.SUCCESS('Sync lock cleared.'))
            progress = get_progress()
            if progress.get('resume_from'):
                self.stdout.write(f"  Will resume from facility {progress['resume_from']}")

        summary = check_for_new_reports(force=options['force'])
        if summary.get('skipped'):
            self.stdout.write(self.style.WARNING(
                f"Skipped: {summary.get('reason', 'unknown')}"
            ))
            return
        if summary.get('error'):
            self.stdout.write(self.style.ERROR(f"Failed: {summary['error']}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Done — checked {summary.get('checked', 0)}, "
            f"updated {summary.get('updated', 0)}, "
            f"unchanged {summary.get('unchanged', 0)}, "
            f"timeouts {summary.get('timed_out', 0)}, "
            f"errors {summary.get('errors', 0)}"
        ))
