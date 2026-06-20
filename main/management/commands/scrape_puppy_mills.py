from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run a full Dog Watch sync (USDA import + APHIS enrichment + geocoding)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-enrich',
            action='store_true',
            help='Only import base USDA licensee data without APHIS enrichment',
        )
        parser.add_argument(
            '--no-news',
            action='store_true',
            help='Include news articles during enrichment',
        )
        parser.add_argument(
            '--force-import',
            action='store_true',
            help='Re-download USDA spreadsheet even if facilities exist',
        )
        parser.add_argument(
            '--reset-enriched',
            action='store_true',
            help='Clear enrichment data before running a full sync',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run a full sync even if the 25-hour interval has not elapsed',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting Dog Watch full sync...')
        from main.dog_watch.scraper import scrape_puppy_mills, run_full_sync, clear_progress
        from main.models import PuppyMillFacility

        if options.get('reset_enriched'):
            reset_count = PuppyMillFacility.objects.update(
                last_scraped_at=None,
                violation_count=0,
                direct_violations=0,
                critical_violations=0,
                inspection_reports=[],
                coordinates_geocoded=False,
                latitude=None,
                longitude=None,
            )
            self.stdout.write(f'Reset {reset_count} facilities for re-enrichment.')

        try:
            if options['no_enrich']:
                summary = scrape_puppy_mills(
                    enrich=False,
                    force_import=options.get('force_import', False),
                )
            else:
                summary = run_full_sync(
                    force=True,
                    fetch_news_articles=not options.get('no_news', False),
                )
        finally:
            clear_progress()

        if summary.get('skipped'):
            self.stdout.write(self.style.WARNING(
                f"Skipped: {summary.get('reason', 'unknown')}"
            ))
            return

        if summary.get('error'):
            self.stdout.write(self.style.ERROR(f"Failed: {summary['error']}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Created: {summary.get('created', 0)}, Updated: {summary.get('updated', 0)}, "
            f"Enriched: {summary.get('enriched', 0)}, Geocoded: {summary.get('geocoded', 0)}, "
            f"On map: {summary.get('mapped_count', '—')}, Errors: {summary.get('errors', 0)}"
        ))
