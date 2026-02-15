"""
Management command to run the ARI event handler.

This command starts a background thread that listens for real-time
call events from Asterisk and updates the database accordingly.

Usage:
    python manage.py run_ari_handler
"""
import signal
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the Asterisk ARI event handler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-reconnect',
            action='store_true',
            help='Exit on connection error instead of reconnecting',
        )

    def handle(self, *args, **options):
        from apps.calls.ari_events import ari_handler

        self.stdout.write(self.style.SUCCESS('Starting ARI event handler...'))

        # Handle shutdown signals
        def signal_handler(signum, frame):
            self.stdout.write('\nShutting down ARI event handler...')
            ari_handler.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            ari_handler.start()

            # Keep main thread alive
            import time
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write('\nShutting down...')
            ari_handler.stop()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
            ari_handler.stop()
            if not options['no_reconnect']:
                raise
