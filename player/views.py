from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from .models import Track
from .services import favourite_tracks, get_listener, toggle_favourite


def _render_list(request, tracks, list_name, empty_message):
    """Render a track list. htmx nav swaps only #main; history restores get the full page."""
    tracks = list(tracks)
    template = "player/track_list.html"
    if request.htmx and not request.htmx.history_restore_request:
        template += "#tracks"
    return render(
        request,
        template,
        {
            "tracks": tracks,
            "queue": [t.as_queue_item() for t in tracks],
            "list_name": list_name,
            "empty_message": empty_message,
        },
    )


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def track_list(request):
    listener = get_listener(request)
    return _render_list(request, Track.objects.with_favourite_flag(listener), "All tracks", "No tracks yet.")


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def favourites(request):
    listener = get_listener(request)
    return _render_list(
        request, favourite_tracks(listener), "Favourites", "No favourites yet. Tap the heart on a track to keep it."
    )


@require_POST
def favourite_toggle(request, pk):
    track = get_object_or_404(Track, pk=pk)
    track.is_fav = toggle_favourite(get_listener(request), track)
    return render(request, "player/fav_button.html", {"t": track})
