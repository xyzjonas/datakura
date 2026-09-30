import pytest

from apps.warehouse.tasks import add


@pytest.fixture(autouse=True)
def eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [(1, 2, 3), (0, 0, 0), (-5, 5, 0), (-1, -1, -2), (10**12, 1, 10**12 + 1)],
)
def test_add_eager(x, y, expected):
    assert add.delay(x, y).get() == expected


def test_add_is_registered_with_app():
    from conf.celery import app

    app.loader.import_default_modules()
    assert "apps.warehouse.tasks.add" in app.tasks


def test_add_rejects_invalid_args():
    with pytest.raises(TypeError):
        add.delay(1, None).get()  # type: ignore[arg-type]
