from pathlib import Path

from django.utils.text import slugify
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3

from django.db.models import Max

from .models import Favourite, Listener, Play, Track

APP_STATIC = Path(__file__).resolve().parent / "static"
AUDIO_DIR = APP_STATIC / "player" / "audio"
COVER_DIR = APP_STATIC / "player" / "covers"

SESSION_KEY = "listener_id"


def get_listener(request):
    """Return the Listener for this browser session, creating one on first visit."""
    listener_id = request.session.get(SESSION_KEY)
    if listener_id:
        listener = Listener.objects.filter(pk=listener_id).first()
        if listener:
            return listener
    listener = Listener.objects.create()
    request.session[SESSION_KEY] = listener.pk
    return listener


def toggle_favourite(listener, track):
    """Add the Track to the Listener's Favourites, or remove it if already there. Returns the new state."""
    deleted, _ = Favourite.objects.filter(listener=listener, track=track).delete()
    if deleted:
        return False
    Favourite.objects.get_or_create(listener=listener, track=track)
    return True


def favourite_tracks(listener):
    """The Listener's Favourites, most recently added first."""
    return Track.objects.with_favourite_flag(listener).filter(favourited_by__listener=listener).order_by(
        "-favourited_by__created_at"
    )


def record_play(listener, track):
    return Play.objects.create(listener=listener, track=track)


def recent_tracks(listener, limit=20):
    """Tracks the Listener has played, newest first, each Track once."""
    return (
        Track.objects.with_favourite_flag(listener)
        .filter(plays__listener=listener)
        .annotate(last_played=Max("plays__played_at"))
        .order_by("-last_played")[:limit]
    )


def parse_filename(stem):
    """'Artist - Title' -> (artist, title). Used when a file has no ID3 tags."""
    artist, sep, title = stem.partition(" - ")
    return (artist.strip(), title.strip()) if sep else ("Unknown artist", stem.strip())


def read_track_file(path, cover_dir=COVER_DIR):
    """Read metadata from an mp3; extract embedded cover art into cover_dir if not already there."""
    audio = MP3(path)
    tags = audio.tags or {}
    fallback_artist, fallback_title = parse_filename(path.stem)

    def tag(key, default):
        frame = tags.get(key)
        return str(frame.text[0]).strip() if frame and frame.text else default

    slug = slugify(path.stem)
    cover_name = ""
    pictures = [frame for key, frame in tags.items() if key.startswith("APIC")] if tags else []
    if pictures:
        ext = "png" if pictures[0].mime == "image/png" else "jpg"
        cover_file = cover_dir / f"{slug}.{ext}"
        if not cover_file.exists():
            cover_dir.mkdir(parents=True, exist_ok=True)
            cover_file.write_bytes(pictures[0].data)
        cover_name = cover_file.name

    return {
        "slug": slug,
        "title": tag("TIT2", fallback_title),
        "artist": tag("TPE1", fallback_artist),
        "album": tag("TALB", ""),
        "duration_seconds": round(audio.info.length, 2),
        "audio_file": path.name,
        "cover_file": cover_name,
    }


def load_catalogue(audio_dir=AUDIO_DIR, cover_dir=COVER_DIR):
    """Create or update a Track per mp3 in audio_dir. Idempotent; returns (created, updated)."""
    created = updated = 0
    for path in sorted(Path(audio_dir).glob("*.mp3")):
        try:
            meta = read_track_file(path, cover_dir)
        except ID3NoHeaderError:
            continue
        _, was_created = Track.objects.update_or_create(
            slug=meta["slug"],
            defaults={
                "title": meta["title"],
                "artist": meta["artist"],
                "album": meta["album"],
                "duration_seconds": meta["duration_seconds"],
                "audio_path": f"player/audio/{meta['audio_file']}",
                "cover_path": f"player/covers/{meta['cover_file']}" if meta["cover_file"] else "",
            },
        )
        created += was_created
        updated += not was_created
    return created, updated
