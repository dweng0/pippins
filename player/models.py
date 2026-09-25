from django.db import models
from django.templatetags.static import static


class Track(models.Model):
    """One playable song in the catalogue. Audio and cover are static file paths."""

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    album = models.CharField(max_length=200, blank=True)
    audio_path = models.CharField(max_length=300)
    cover_path = models.CharField(max_length=300, blank=True)
    duration_seconds = models.FloatField(default=0)

    class Meta:
        ordering = ["artist", "title"]

    def __str__(self):
        return f"{self.artist} - {self.title}"

    @property
    def audio_url(self):
        return static(self.audio_path)

    @property
    def cover_url(self):
        return static(self.cover_path or "player/covers/placeholder.svg")

    def as_queue_item(self):
        """Shape handed to the browser player (see player/static/player/player.js)."""
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "src": self.audio_url,
            "cover": self.cover_url,
            "duration": self.duration_seconds,
        }


class Listener(models.Model):
    """The person using the player; owns all per-person state (ADR-0001). Anonymous until accounts exist."""

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Listener {self.pk}"
