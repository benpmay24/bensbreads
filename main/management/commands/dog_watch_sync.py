from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Dog Watch data collector — refresh USDA list, then check breeders for new APHIS reports. '
        'Run as a Render Cron Job, not from the web app.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-check every breeder even if checked within the last 24 hours',
        )
        parser.add_argument(
            '--skip-usda-import',
            action='store_true',
            help='Skip refreshing the USDA breeder/dealer list before checking reports',
        )
        parser.add_argument(
            '--clear-lock',
            action='store_true',
            help='Clear a stuck collection lock before running',
        )

    def handle(self, *args, **options):
        from main.dog_watch.collector import run_collection
        from main.dog_watch.sync_state import force_clear_lock, get_progress

        if options['clear_lock']:
            force_clear_lock()
            self.stdout.write(self.style.SUCCESS('Collection lock cleared.'))
            progress = get_progress()
            if progress.get('resume_from'):
                self.stdout.write(f"  Resuming from facility {progress['resume_from']}")

        summary = run_collection(
            force=options['force'],
            import_usda=not options['skip_usda_import'],
        )
        if summary.get('skipped'):
            self.stdout.write(self.style.WARNING(
                f"Skipped: {summary.get('reason', 'unknown')}"
            ))
            return
        if summary.get('error'):
            self.stdout.write(self.style.ERROR(f"Failed: {summary['error']}"))
            return

        usda_msg = ''
        if 'usda_created' in summary or 'usda_updated' in summary:
            usda_msg = (
                f", USDA import: {summary.get('usda_created', 0)} new, "
                f"{summary.get('usda_updated', 0)} updated"
            )
        self.stdout.write(self.style.SUCCESS(
            f"Done — checked {summary.get('checked', 0)}, "
            f"updated {summary.get('updated', 0)}, "
            f"unchanged {summary.get('unchanged', 0)}, "
            f"timeouts {summary.get('timed_out', 0)}, "
            f"errors {summary.get('errors', 0)}"
            f"{usda_msg}"
        ))
