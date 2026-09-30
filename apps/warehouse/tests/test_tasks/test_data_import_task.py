import json

import pytest

from apps.warehouse.core.services.data_import.staging import read_staged
from apps.warehouse.core.services.data_import.staged_import import (
    StagedWarehouse,
    run_staged_import,
)
from apps.warehouse.core.services.data_import.staging import STAGING_DIR
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.test_management.test_import_customers import (
    SAMPLE as CUSTOMER,
)
from apps.warehouse.tests.test_management.test_import_products import (
    SAMPLE as PRODUCT,
)


@pytest.fixture
def staged(celery_inline, tmp_path):
    def stage(name: str, content: object) -> str:
        path = tmp_path / STAGING_DIR / "job" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = content if isinstance(content, bytes) else json.dumps(content).encode()
        path.write_bytes(raw)
        return f"{STAGING_DIR}/job/{name}"

    return stage


@pytest.mark.django_db
def test_progress_is_reported_through_all_stages(staged):
    snapshots = []
    place = {
        "Code": "L-1",
        "StockItems": [{"StockProductCode": "94-1801-10-160", "Value": 1}],
    }
    warehouses: list[StagedWarehouse] = [
        {"warehouse": "W", "path": staged("w.json", {"WarehousePlaces": [place]})}
    ]

    envelope = run_staged_import(
        staged("p.json", [PRODUCT]),
        staged("c.json", [CUSTOMER]),
        warehouses,
        sink=snapshots.append,
    )

    assert envelope["status"] == "succeeded"
    percents = [s.percent for s in snapshots]
    assert percents == sorted(percents), "progress must never go backwards"
    assert percents[-1] == 100.0
    assert [s.stage for s in snapshots if s.stage][0] == "products"
    assert {s.stage for s in snapshots} >= {"products", "customers", "warehouse 'W'"}
    assert {"validating", "importing", "done"} <= {s.phase for s in snapshots}


@pytest.mark.django_db
def test_failed_import_returns_envelope_and_removes_files(staged, tmp_path):
    path = staged("p.json", b"not json")

    envelope = run_staged_import(path, None, [])

    assert envelope["status"] == "failed"
    assert "products: Invalid JSON" in envelope["error"]
    assert not (tmp_path / path).exists()


@pytest.mark.django_db
def test_missing_staged_file_is_a_crash_not_an_envelope(staged, tmp_path):
    # staged files vanished (e.g. worker without the shared storage): loud failure
    with pytest.raises(Exception):
        run_staged_import(f"{STAGING_DIR}/job/missing.json", None, [])


@pytest.mark.django_db
def test_task_is_registered_and_publishes_state(celery_inline, staged):
    from apps.warehouse.tasks import run_data_import

    app = celery_inline
    app.loader.import_default_modules()
    assert "data_import.run" in app.tasks

    result = run_data_import.apply_async(args=[staged("p.json", [PRODUCT]), None, []])

    assert result.get()["status"] == "succeeded"
    assert StockProduct.objects.filter(code=PRODUCT["Code"]).exists()


def test_staging_roundtrip(celery_inline, tmp_path):
    from django.core.files.base import ContentFile

    from apps.warehouse.core.services.data_import.staging import (
        discard_staged,
        stage_upload,
    )

    path = stage_upload("job-1", "products", ContentFile(b"[1]"))

    assert read_staged(path) == b"[1]"
    discard_staged([path, "data-import/job-1/already-gone.json"])
    assert not (tmp_path / path).exists()
