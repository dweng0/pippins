from django.core.management import call_command
from django.core.management.base import BaseCommand

from player.services import prune_listeners


class Command(BaseCommand):
    help = "Delete expired sessions and the Listeners they orphaned (with their Favourites and Plays)."

    def handle(self, *args, **options):
        call_command("clearsessions")
        self.stdout.write(f"Pruned {prune_listeners()} orphaned Listener(s).")
