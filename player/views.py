from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from .models import Track
from .services import favourite_tracks, get_listener, recent_tracks, record_play, toggle_favourite


def _render_list(request, tracks, list_name, empty_message, q=None, hero=False):
    """Render a track list. htmx nav swaps only #main; the search box swaps only the rows;
    history restores get the full page."""
    tracks = list(tracks)
    template = "player/track_list.html"
    if request.htmx and not request.htmx.history_restore_request:
        template += "#rows" if request.htmx.trigger_name == "q" else "#tracks"
    return render(
        request,
        template,
        {
            "tracks": tracks,
            "queue": [t.as_queue_item() for t in tracks],
            "list_name": list_name,
            "empty_message": empty_message,
            "q": q,
            "hero": hero,
        },
    )


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def track_list(request):
    listener = get_listener(request, create=False)
    q = request.GET.get("q", "").strip()
    tracks = Track.objects.with_favourite_flag(listener).search(q)
    empty = f"No tracks match \u201c{q}\u201d." if q else "No tracks yet."
    return _render_list(request, tracks, "All tracks", empty, q=q, hero=True)


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def favourites(request):
    listener = get_listener(request, create=False)
    return _render_list(
        request, favourite_tracks(listener), "Favourites", "No favourites yet. Tap the heart on a track to keep it."
    )


@require_POST
def favourite_toggle(request, pk):
    track = get_object_or_404(Track, pk=pk)
    listener = get_listener(request)
    toggle_favourite(listener, track)
    track = Track.objects.with_favourite_flag(listener).get(pk=pk)  # is_fav from the one annotation, like the lists
    return render(request, "player/fav_button.html", {"t": track})


@vary_on_headers("HX-Request", "HX-History-Restore-Request")
def recent(request):
    listener = get_listener(request, create=False)
    return _render_list(request, recent_tracks(listener), "Recently played", "Nothing played yet.")


@require_POST
def played(request, pk):
    track = get_object_or_404(Track, pk=pk)  # before get_listener: a bad id must not create a Listener
    record_play(get_listener(request), track)
    return HttpResponse(status=204)
