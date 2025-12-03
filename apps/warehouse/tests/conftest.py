import pytest


@pytest.fixture(autouse=True)
def use_utc_timezone(settings):
    settings.USE_TZ = True
    settings.TIME_ZONE = "UTC"
