from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Check all dog breeders for new APHIS inspection reports (runs every 24h)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run even if the last sync was less than 24 hours ago',
        )

    def handle(self, *args, **options):
        from main.dog_watch.scraper import check_for_new_reports

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
            f"errors {summary.get('errors', 0)}"
        ))
