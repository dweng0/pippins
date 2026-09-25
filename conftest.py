import pytest


@pytest.fixture(autouse=True)
def plain_static_storage(settings):
    """Tests run DEBUG=False without collectstatic, where the manifest storage can't resolve names.
    The prod path is covered by the collected_static fixture in player/tests.py."""
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

