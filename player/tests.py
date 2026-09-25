from urllib.parse import quote

import pytest
from django.urls import reverse

from player.models import Listener, Track
from player.services import load_catalogue, parse_filename


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

    untagged = Track.objects.get(slug="mr-smith-3djc")
    assert (untagged.title, untagged.artist) == ("3DJC", "Mr Smith")
    assert untagged.cover_path == ""
    assert untagged.cover_url.endswith("placeholder.svg")


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
    url = "/static/player/audio/" + quote("Komiku - Bad Guys HQ.mp3")
    response = client.get(url, HTTP_RANGE="bytes=1000-1999")
    assert response.status_code == 206
    assert response["Content-Range"].startswith("bytes 1000-1999/")
    assert response["Content-Type"] == "audio/mpeg"
    assert len(b"".join(response.streaming_content)) == 1000


def test_mmss_filter_formats_durations():
    from player.templatetags.player_tags import mmss

    assert mmss(132.4) == "2:12"
    assert mmss(59) == "0:59"
    assert mmss(None) == "0:00"
