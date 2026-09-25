from django.core.management.base import BaseCommand

from player.services import load_catalogue


class Command(BaseCommand):
    help = "Load the bundled sample mp3s into the Track catalogue (idempotent)."

    def handle(self, *args, **options):
        created, updated = load_catalogue()
        self.stdout.write(self.style.SUCCESS(f"Tracks: {created} created, {updated} updated"))
