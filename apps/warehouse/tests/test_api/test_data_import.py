import json
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.warehouse.models.customer import Customer
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import Warehouse, WarehouseItem
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.test_management.test_import_customers import (
    SAMPLE as CUSTOMER,
)
from apps.warehouse.tests.test_management.test_import_products import (
    SAMPLE as PRODUCT,
)

URL = "/api/v1/data-import"
PRODUCT_CODE = PRODUCT["Code"]


def upload(data, name="data.json") -> SimpleUploadedFile:
    raw = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
    return SimpleUploadedFile(name, raw, content_type="application/json")


def stock(*items: tuple[str, float], place: str = "AA-01-00") -> dict:
    return {
        "WarehousePlaces": [
            {
                "Code": place,
                "StockItems": [
                    {"StockProductCode": code, "Value": value, "Price": 1}
                    for code, value in items
                ],
            }
        ]
    }


@pytest.fixture
def client(user, celery_inline) -> Client:
    client = Client()
    client.force_login(user)
    return client


def customers_qs():
    return Customer.objects.exclude(code="ghost-customer")


def start(client: Client, data: dict):
    return client.post(URL, data)


def run(client: Client, data: dict) -> dict:
    """Starts the import (tasks run inline in tests) and returns the job status"""
    response = start(client, data)
    assert response.status_code == 202, response.content
    job_id = response.json()["data"]["job_id"]
    status = client.get(f"{URL}/jobs/{job_id}")
    assert status.status_code == 200, status.content
    return status.json()["data"]


def staged_files(tmp_path) -> list:
    return [p for p in (tmp_path / "data-import").rglob("*") if p.is_file()]


@pytest.mark.django_db
def test_requires_authentication(celery_inline):
    anonymous = Client()

    assert anonymous.post(URL, {"products_file": upload([PRODUCT])}).status_code == 401
    assert anonymous.get(f"{URL}/jobs/{uuid.uuid4()}").status_code == 401


@pytest.mark.django_db
def test_start_returns_job_id_and_job_succeeds(client):
    response = start(client, {"products_file": upload([PRODUCT])})

    assert response.status_code == 202
    job_id = response.json()["data"]["job_id"]
    assert str(uuid.UUID(job_id)) == job_id
    status = client.get(f"{URL}/jobs/{job_id}").json()["data"]
    assert status["job_id"] == job_id
    assert status["state"] == "succeeded"
    assert status["percent"] == 100
    assert status["error"] is None
    assert status["result"]["products"]["created"] == 1


@pytest.mark.django_db
def test_full_import_in_dependency_order(client):
    status = run(
        client,
        {
            # stock refers to a product coming from the very same request
            "products_file": upload([PRODUCT]),
            "customers_file": upload([CUSTOMER]),
            "warehouse_ids": ["Centrála", "Sklad 2"],
            "warehouse_files": [
                upload(stock((PRODUCT_CODE, 1.5))),
                upload(stock((PRODUCT_CODE, 2), place="BB-01-00")),
            ],
        },
    )

    assert status["state"] == "succeeded", status
    data = status["result"]
    assert data["products"]["created"] == 1
    assert data["customers"]["created"] == 1
    assert data["customers"]["contacts"] == 1
    assert [w["warehouse"] for w in data["warehouses"]] == ["Centrála", "Sklad 2"]
    assert all(w["items_created"] == 1 for w in data["warehouses"])
    assert StockProduct.objects.filter(code=PRODUCT_CODE).exists()
    assert customers_qs().count() == 1
    assert WarehouseItem.objects.count() == 2
    assert set(Warehouse.objects.values_list("name", flat=True)) == {
        "Centrála",
        "Sklad 2",
    }


@pytest.mark.django_db
@pytest.mark.parametrize("section", ["products", "customers", "warehouse"])
def test_sections_are_optional(client, section):
    StockProductFactory(code="P-1")
    payloads = {
        "products": {"products_file": upload([PRODUCT])},
        "customers": {"customers_file": upload([CUSTOMER])},
        "warehouse": {
            "warehouse_ids": ["W"],
            "warehouse_files": [upload(stock(("P-1", 1)))],
        },
    }

    status = run(client, payloads[section])

    assert status["state"] == "succeeded", status
    data = status["result"]
    assert (data["products"] is not None) == (section == "products")
    assert (data["customers"] is not None) == (section == "customers")
    assert bool(data["warehouses"]) == (section == "warehouse")


@pytest.mark.django_db
def test_nothing_to_import_is_rejected(client):
    response = start(client, {})

    assert response.status_code == 400
    assert "Nothing to import" in response.json()["error"]["exception"]


@pytest.mark.django_db
def test_failure_in_last_step_rolls_everything_back(client):
    status = run(
        client,
        {
            "products_file": upload([PRODUCT]),
            "customers_file": upload([CUSTOMER]),
            "warehouse_ids": ["Centrála"],
            "warehouse_files": [upload(stock(("DOES-NOT-EXIST", 1)))],
        },
    )

    assert status["state"] == "failed"
    assert status["result"] is None
    assert "warehouse 'Centrála'" in status["error"]
    assert "DOES-NOT-EXIST" in status["error"]
    assert not StockProduct.objects.filter(code=PRODUCT_CODE).exists()
    assert not customers_qs().exists()
    assert not Warehouse.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "files, message",
    [
        ({"products_file": b"not json"}, "products: Invalid JSON"),
        ({"products_file": b"[{}]"}, "products: Record #0"),
        ({"customers_file": b"[{}]"}, "customers: Record #0"),
        ({"products_file": b"\xff\xfe\x00"}, "products: Input is not valid UTF-8"),
    ],
)
def test_invalid_file_content_fails_the_job_naming_the_section(client, files, message):
    status = run(client, {k: upload(v) for k, v in files.items()})

    assert status["state"] == "failed"
    assert message in status["error"]


@pytest.mark.django_db
def test_staged_files_are_removed_after_success_and_failure(client, tmp_path):
    run(client, {"customers_file": upload([CUSTOMER])})
    run(client, {"products_file": upload(b"not json")})

    assert staged_files(tmp_path) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ids, file_count",
    [(["A"], 0), ([], 1), (["A", "B"], 1), (["A"], 2)],
)
def test_warehouse_ids_and_files_must_pair_up(client, ids, file_count, tmp_path):
    StockProductFactory(code="P-1")

    response = start(
        client,
        {
            "warehouse_ids": ids,
            "warehouse_files": [upload(stock(("P-1", 1))) for _ in range(file_count)],
        },
    )

    assert response.status_code == 400
    assert "warehouse ids" in response.json()["error"]["exception"]
    assert not Warehouse.objects.exists()
    assert staged_files(tmp_path) == []


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["", "   ", "W" * 51])
def test_bad_warehouse_name_is_rejected_before_queueing(client, name, tmp_path):
    StockProductFactory(code="P-1")

    response = start(
        client,
        {"warehouse_ids": [name], "warehouse_files": [upload(stock(("P-1", 1)))]},
    )

    assert response.status_code == 400
    assert not Warehouse.objects.exists()
    assert staged_files(tmp_path) == []


@pytest.mark.django_db
def test_same_warehouse_twice_is_ok_and_item_import_repeats(client):
    StockProductFactory(code="P-1")

    status = run(
        client,
        {
            "warehouse_ids": ["W", "W"],
            "warehouse_files": [
                upload(stock(("P-1", 1), place="L-1")),
                upload(stock(("P-1", 2), place="L-1")),
            ],
        },
    )

    first, second = status["result"]["warehouses"]
    assert first["warehouse_created"] and not second["warehouse_created"]
    assert second["locations_existing"] == 1
    assert Warehouse.objects.count() == 1
    assert WarehouseItem.objects.count() == 2


@pytest.mark.django_db
def test_import_is_repeatable_for_products_and_customers(client):
    run(
        client,
        {"products_file": upload([PRODUCT]), "customers_file": upload([CUSTOMER])},
    )

    status = run(
        client,
        {"products_file": upload([PRODUCT]), "customers_file": upload([CUSTOMER])},
    )

    data = status["result"]
    assert (data["products"]["updated"], data["customers"]["updated"]) == (1, 1)


@pytest.mark.django_db
def test_utf8_bom_files_are_accepted(client):
    raw = b"\xef\xbb\xbf" + json.dumps([CUSTOMER]).encode("utf-8")

    assert run(client, {"customers_file": upload(raw)})["state"] == "succeeded"


# ---- job status endpoint


@pytest.mark.django_db
def test_unknown_job_is_pending(client):
    status = client.get(f"{URL}/jobs/{uuid.uuid4()}").json()["data"]

    assert status["state"] == "pending"
    assert status["percent"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "job_id", ["nope", "123", "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"]
)
def test_malformed_job_id_is_404(client, job_id):
    assert client.get(f"{URL}/jobs/{job_id}").status_code == 404


@pytest.mark.django_db
def test_running_job_reports_progress(client, celery_inline):
    job_id = str(uuid.uuid4())
    celery_inline.backend.store_result(
        job_id,
        {
            "stage": "products",
            "phase": "importing",
            "stage_done": 50,
            "stage_total": 200,
            "percent": 12.5,
        },
        "PROGRESS",
    )

    status = client.get(f"{URL}/jobs/{job_id}").json()["data"]

    assert status == {
        "job_id": job_id,
        "state": "running",
        "stage": "products",
        "phase": "importing",
        "stage_done": 50,
        "stage_total": 200,
        "percent": 12.5,
        "result": None,
        "error": None,
    }


@pytest.mark.django_db
def test_started_job_without_progress_is_running(client, celery_inline):
    job_id = str(uuid.uuid4())
    celery_inline.backend.store_result(job_id, None, "STARTED")

    status = client.get(f"{URL}/jobs/{job_id}").json()["data"]

    assert (status["state"], status["percent"]) == ("running", 0)


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["FAILURE", "REVOKED"])
def test_crashed_job_is_reported_as_failed(client, celery_inline, state):
    job_id = str(uuid.uuid4())
    celery_inline.backend.store_result(job_id, RuntimeError("worker died"), state)

    status = client.get(f"{URL}/jobs/{job_id}").json()["data"]

    assert status["state"] == "failed"
    assert "Import interrupted" in status["error"]
