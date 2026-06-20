from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import USDA breeder list and fetch initial APHIS data (one-time setup)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-import USDA spreadsheet even if facilities exist',
        )

    def handle(self, *args, **options):
        from main.models import PuppyMillFacility
        from main.dog_watch.scraper import check_for_new_reports, import_usda_facilities

        if options['force'] or PuppyMillFacility.objects.count() == 0:
            self.stdout.write('Importing USDA licensee data…')
            import_summary = import_usda_facilities()
            if import_summary.get('error'):
                self.stdout.write(self.style.ERROR(f"Import failed: {import_summary['error']}"))
                return
            self.stdout.write(
                f"USDA: {import_summary.get('created', 0)} created, "
                f"{import_summary.get('updated', 0)} updated"
            )

        self.stdout.write('Fetching APHIS inspection data…')
        summary = check_for_new_reports(force=True)
        if summary.get('skipped'):
            self.stdout.write(self.style.WARNING(f"Skipped: {summary.get('reason')}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Done — checked {summary.get('checked', 0)}, "
            f"initialized/updated {summary.get('updated', 0) + summary.get('initialized', 0)}"
        ))
