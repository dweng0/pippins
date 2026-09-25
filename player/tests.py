import pytest
from django.conf import settings as django_settings
from django.urls import reverse

from player.models import Listener, Track
from player.services import AUDIO_DIR, load_catalogue, parse_filename


@pytest.fixture
def catalogue(tmp_path):
    """Load the bundled mp3s, writing extracted covers to a temp dir (not the repo)."""
    load_catalogue(cover_dir=tmp_path)
    return tmp_path


def test_parse_filename_splits_artist_and_title():
    assert parse_filename("Mr Smith - 3DJC") == ("Mr Smith", "3DJC")
    assert parse_filename("NoSeparator") == ("Unknown artist", "NoSeparator")


@pytest.mark.django_db
def test_load_catalogue_reads_tags_and_falls_back_to_filename(catalogue):
    assert Track.objects.count() == 6

    tagged = Track.objects.get(slug="komiku-bad-guys-hq")
    assert (tagged.title, tagged.artist, tagged.album) == ("Bad Guys HQ", "Komiku", "THE GIRL WITH THE BASEBALL BAT")
    assert tagged.cover_path == "player/covers/komiku-bad-guys-hq.jpg"
    assert (catalogue / "komiku-bad-guys-hq.jpg").exists()
    assert tagged.duration_seconds > 60

    no_cover = Track.objects.get(slug="mr-smith-3djc")
    assert (no_cover.title, no_cover.artist) == ("3DJC", "Mr Smith")
    assert no_cover.audio_path == "player/audio/mr-smith-3djc.mp3"
    assert no_cover.cover_path == ""
    assert no_cover.cover_url.endswith("placeholder.svg")


@pytest.mark.django_db
def test_untagged_file_falls_back_to_filename(tmp_path):
    import shutil

    from mutagen.id3 import ID3

    audio = tmp_path / "audio"
    audio.mkdir()
    copy = audio / "Some Artist - Some Title.mp3"
    shutil.copy(AUDIO_DIR / "mr-smith-3djc.mp3", copy)
    ID3(copy).delete()

    load_catalogue(audio_dir=audio, cover_dir=tmp_path)
    track = Track.objects.get()
    assert (track.slug, track.artist, track.title) == ("some-artist-some-title", "Some Artist", "Some Title")


@pytest.mark.django_db
def test_load_catalogue_is_idempotent(tmp_path):
    assert load_catalogue(cover_dir=tmp_path) == (6, 0)
    assert load_catalogue(cover_dir=tmp_path) == (0, 6)
    assert Track.objects.count() == 6


@pytest.mark.django_db
def test_get_listener_is_stable_per_session(client):
    client.get(reverse("player:track_list"))
    first = client.session["listener_id"]
    client.get(reverse("player:track_list"))
    assert client.session["listener_id"] == first
    assert Listener.objects.count() == 1


@pytest.mark.django_db
def test_new_session_gets_new_listener(client):
    client.get(reverse("player:track_list"))
    client.cookies.clear()
    client.get(reverse("player:track_list"))
    assert Listener.objects.count() == 2


@pytest.mark.django_db
def test_track_list_full_page_includes_player_and_queue_data(client, catalogue):
    response = client.get(reverse("player:track_list"))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'data-cy="player"' in body
    assert 'id="list-data"' in body
    assert body.count('data-cy="track-row"') == 6
    assert "HX-Request" in response["Vary"]


@pytest.mark.django_db
def test_track_list_htmx_request_returns_partial(client, catalogue):
    response = client.get(reverse("player:track_list"), HTTP_HX_REQUEST="true")
    body = response.content.decode()
    assert body.count('data-cy="track-row"') == 6
    assert 'data-cy="player"' not in body


@pytest.mark.django_db
def test_history_restore_gets_full_page(client, catalogue):
    response = client.get(
        reverse("player:track_list"), HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true"
    )
    assert 'data-cy="player"' in response.content.decode()


def test_static_mp3_supports_range_requests(client, settings):
    # pytest-django runs DEBUG=False without collectstatic; let WhiteNoise resolve via finders.
    settings.WHITENOISE_USE_FINDERS = True
    settings.WHITENOISE_AUTOREFRESH = True
    url = "/static/player/audio/komiku-bad-guys-hq.mp3"
    response = client.get(url, HTTP_RANGE="bytes=1000-1999")
    assert response.status_code == 206
    assert response["Content-Range"].startswith("bytes 1000-1999/")
    assert response["Content-Type"] == "audio/mpeg"
    assert len(b"".join(response.streaming_content)) == 1000


# Captured at import, before conftest's autouse fixture swaps in plain storage for the other tests.
PROD_STATIC_STORAGE = django_settings.STORAGES["staticfiles"]


@pytest.fixture
def collected_static(settings, tmp_path):
    """The prod static path: collectstatic into a fresh STATIC_ROOT, WhiteNoise serving from it (no finders)."""
    from django.core.management import call_command

    settings.STORAGES = {**settings.STORAGES, "staticfiles": PROD_STATIC_STORAGE}
    settings.STATIC_ROOT = tmp_path / "static"
    settings.WHITENOISE_USE_FINDERS = False
    settings.WHITENOISE_AUTOREFRESH = False
    call_command("collectstatic", "--noinput", verbosity=0)
    return settings.STATIC_ROOT


def test_prod_static_serves_hashed_immutable_audio_with_ranges(client, collected_static):
    from django.templatetags.static import static

    url = static("player/audio/komiku-bad-guys-hq.mp3")
    assert url != "/static/player/audio/komiku-bad-guys-hq.mp3"  # content-hashed name

    response = client.get(url, HTTP_RANGE="bytes=0-1023")
    assert response.status_code == 206
    assert "immutable" in response["Cache-Control"]
    assert len(b"".join(response.streaming_content)) == 1024

    assert client.get(url, HTTP_RANGE="bytes=999999999-").status_code == 416


def test_prod_static_js_is_hashed_so_deploys_never_serve_stale_code(client, collected_static):
    from django.templatetags.static import static

    url = static("player/player.js")
    assert url.startswith("/static/player/player.") and url != "/static/player/player.js"
    response = client.get(url)
    assert response.status_code == 200
    assert "immutable" in response["Cache-Control"]


def test_mmss_filter_formats_durations():
    from player.templatetags.player_tags import mmss

    assert mmss(132.4) == "2:12"
    assert mmss(59) == "0:59"
    assert mmss(None) == "0:00"


@pytest.mark.django_db
def test_favourite_toggle_adds_then_removes(client, catalogue):
    from player.models import Favourite

    track = Track.objects.first()
    url = reverse("player:favourite_toggle", args=[track.pk])

    response = client.post(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert 'data-fav="true"' in response.content.decode()
    assert Favourite.objects.count() == 1

    response = client.post(url, HTTP_HX_REQUEST="true")
    assert 'data-fav="false"' in response.content.decode()
    assert Favourite.objects.count() == 0


@pytest.mark.django_db
def test_favourite_toggle_rejects_get(client, catalogue):
    track = Track.objects.first()
    assert client.get(reverse("player:favourite_toggle", args=[track.pk])).status_code == 405


@pytest.mark.django_db
def test_favourites_view_lists_only_this_listeners_favourites(client, catalogue):
    a, b = Track.objects.all()[:2]
    client.post(reverse("player:favourite_toggle", args=[a.pk]))

    body = client.get(reverse("player:favourites")).content.decode()
    assert body.count('data-cy="track-row"') == 1
    assert a.title in body

    client.cookies.clear()  # a different Listener sees none
    body = client.get(reverse("player:favourites")).content.decode()
    assert body.count('data-cy="track-row"') == 0
    assert 'data-cy="empty"' in body


@pytest.mark.django_db
def test_track_list_marks_favourites(client, catalogue):
    track = Track.objects.first()
    client.post(reverse("player:favourite_toggle", args=[track.pk]))
    body = client.get(reverse("player:track_list")).content.decode()
    assert body.count('data-fav="true"') == 1
    assert body.count('data-fav="false"') == 5


@pytest.mark.django_db
def test_search_matches_title_artist_or_album_case_insensitively(catalogue):
    assert Track.objects.search("komiku").count() == 2
    assert Track.objects.search("PUNK").count() == 1
    assert Track.objects.search("hyper metal").count() == 2  # album
    assert Track.objects.search("pew").count() == 1
    assert Track.objects.search("  ").count() == 6
    assert Track.objects.search("nothing-like-this").count() == 0


@pytest.mark.django_db
def test_search_box_gets_rows_partial_only(client, catalogue):
    response = client.get(
        reverse("player:track_list"), {"q": "komiku"}, HTTP_HX_REQUEST="true", HTTP_HX_TRIGGER_NAME="q"
    )
    body = response.content.decode()
    assert body.count('data-cy="track-row"') == 2
    assert 'id="list-data"' in body  # Queue source follows the filtered list
    assert 'data-cy="list-title"' not in body


@pytest.mark.django_db
def test_search_full_page_keeps_query_and_shows_empty_message(client, catalogue):
    body = client.get(reverse("player:track_list"), {"q": "zzz"}).content.decode()
    assert 'value="zzz"' in body
    assert "No tracks match" in body


@pytest.mark.django_db
def test_favourites_page_has_no_search_box(client, catalogue):
    assert 'data-cy="search"' not in client.get(reverse("player:favourites")).content.decode()


@pytest.mark.django_db
def test_played_records_a_play(client, catalogue):
    from player.models import Play

    track = Track.objects.first()
    response = client.post(reverse("player:played", args=[track.pk]))
    assert response.status_code == 204
    assert Play.objects.get().track == track


@pytest.mark.django_db
def test_recent_is_newest_first_and_deduped(client, catalogue):
    a, b = Track.objects.all()[:2]
    for t in (a, b, a):
        client.post(reverse("player:played", args=[t.pk]))

    body = client.get(reverse("player:recent")).content.decode()
    assert body.count('data-cy="track-row"') == 2
    assert body.index(a.title) < body.index(b.title)


@pytest.mark.django_db
def test_queue_items_carry_played_url(catalogue):
    track = Track.objects.first()
    assert track.as_queue_item()["playedUrl"] == f"/tracks/{track.pk}/played/"


@pytest.mark.django_db
def test_mascot_is_favicon_and_logo(client):
    body = client.get(reverse("player:track_list")).content.decode()
    assert '<link rel="icon" href="/static/player/pippins.svg"' in body
    assert 'data-cy="mascot"' in body
