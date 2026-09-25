from django.shortcuts import render
from django.views.decorators.vary import vary_on_headers

from .models import Track
from .services import get_listener


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def track_list(request):
    get_listener(request)
    tracks = list(Track.objects.all())
    template = "player/track_list.html"
    # htmx nav swaps only #main; history restores get the full page (htmx extracts #main).
    if request.htmx and not request.htmx.history_restore_request:
        template += "#tracks"
    return render(
        request,
        template,
        {"tracks": tracks, "queue": [t.as_queue_item() for t in tracks], "list_name": "All tracks"},
    )
