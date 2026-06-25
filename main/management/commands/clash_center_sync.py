from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Collect Clash Royale ranked battle data from the Royale API and store it '
        'in the database. Run as a Render Cron Job; the web UI reads DB only.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run even if the sync interval has not elapsed',
        )
        parser.add_argument(
            '--clear-lock',
            action='store_true',
            help='Clear a stuck collection lock before running',
        )
        parser.add_argument(
            '--cards-only',
            action='store_true',
            help='Only refresh the card catalog',
        )

    def handle(self, *args, **options):
        from main.clash_center.collector import run_collection, sync_cards
        from main.clash_center.api_client import ClashRoyaleClient
        from main.clash_center.sync_state import force_clear_lock
        from main.models import ClashCenterSyncState

        if options['clear_lock']:
            force_clear_lock()
            self.stdout.write(self.style.SUCCESS('Collection lock cleared.'))
            if not options['force'] and not options['cards_only']:
                return

        if options['cards_only']:
            client = ClashRoyaleClient()
            if not client.configured():
                self.stdout.write(self.style.ERROR('CLASH_ROYALE_API_TOKEN is required'))
                return
            state = ClashCenterSyncState.load()
            count = sync_cards(client, state, force=True)
            self.stdout.write(self.style.SUCCESS(f'Card catalog synced ({count} new cards).'))
            return

        summary = run_collection(
            force=options['force'],
            skip_if_due=not options['force'],
        )

        if summary.get('skipped'):
            self.stdout.write(self.style.WARNING(
                f"Skipped: {summary.get('reason', 'unknown')}"
            ))
            return
        if summary.get('error'):
            self.stdout.write(self.style.ERROR(f"Failed: {summary['error']}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Done — players checked {summary.get('players_checked', 0)}, "
            f"battles added {summary.get('battles_added', 0)}, "
            f"seen {summary.get('battles_seen', 0)}, "
            f"total battles {summary.get('total_battles', 0)}"
        ))
