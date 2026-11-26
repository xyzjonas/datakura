import uuid

import pytest
from django.test import Client
from ninja.testing import TestClient

from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.api.routes.norms import routes as norm_routes
from apps.warehouse.api.routes.product import routes as product_routes
from apps.warehouse.models.product import Norm, NormType, StockProduct
from apps.warehouse.tests.factories.product import NormFactory, StockProductFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(norm_routes)


@pytest.fixture
def products() -> TestClient:
    return TestClient(product_routes)


def payload(**overrides):
    return {"code": "84", "type": "DIN", "equivalent_ids": [], **overrides}


def test_create_norm(client):
    response = client.post("/", json=payload())

    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["code"], data["type"], data["label"]) == ("84", "DIN", "DIN 84")
    assert data["equivalents"] == []
    assert Norm.objects.get().label == "DIN 84"


def test_create_norm_with_equivalents_is_symmetric(client):
    iso = NormFactory(type=NormType.ISO, code="1207")

    response = client.post("/", json=payload(equivalent_ids=[iso.pk]))

    assert [e["label"] for e in response.json()["data"]["equivalents"]] == ["ISO 1207"]
    assert [n.label for n in iso.equivalents.all()] == ["DIN 84"]


@pytest.mark.parametrize(
    "body",
    [
        payload(code=""),
        payload(code="   "),
        payload(type="GOST"),
        payload(code="x" * 65),
    ],
)
def test_create_norm_validation(client, body):
    assert client.post("/", json=body).status_code == 422
    assert not Norm.objects.exists()


def test_code_is_unique_within_type_only(client):
    NormFactory(type=NormType.DIN, code="84")

    with pytest.raises(ApiBaseException, match="already exists"):
        client.post("/", json=payload())
    other_namespace = client.post("/", json=payload(type="ISO"))

    assert other_namespace.status_code == 200
    assert Norm.objects.count() == 2


def test_create_norm_unknown_equivalent(client):
    with pytest.raises(ApiBaseException, match="Unknown norms"):
        client.post("/", json=payload(equivalent_ids=[999999]))

    assert not Norm.objects.exists()


def test_get_norm(client):
    iso = NormFactory(type=NormType.ISO, code="1207")
    norm = NormFactory(equivalents=[iso])

    data = client.get(f"/{norm.pk}").json()["data"]

    assert data["label"] == norm.label
    assert [e["label"] for e in data["equivalents"]] == ["ISO 1207"]
    with pytest.raises(NotFoundException):
        client.get("/999")


def test_update_norm(client):
    norm = NormFactory(type=NormType.DIN, code="84")
    iso = NormFactory(type=NormType.ISO, code="1207")
    csn = NormFactory(type=NormType.CSN, code="02", equivalents=[norm])

    response = client.put(
        f"/{norm.pk}", json=payload(code="85", equivalent_ids=[iso.pk])
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["label"] == "DIN 85"
    assert [e["label"] for e in data["equivalents"]] == ["ISO 1207"]
    assert not csn.equivalents.exists()  # alias dropped on both sides


def test_update_norm_to_taken_code(client):
    NormFactory(type=NormType.DIN, code="85")
    norm = NormFactory(type=NormType.DIN, code="84")

    with pytest.raises(ApiBaseException, match="already exists"):
        client.put(f"/{norm.pk}", json=payload(code="85"))


def test_update_cannot_alias_norm_to_itself(client):
    norm = NormFactory()

    response = client.put(
        f"/{norm.pk}", json=payload(code=norm.code, equivalent_ids=[norm.pk])
    )

    assert response.status_code == 200
    assert response.json()["data"]["equivalents"] == []


def test_update_and_delete_missing_norm(client):
    with pytest.raises(NotFoundException):
        client.put("/999", json=payload())
    with pytest.raises(NotFoundException):
        client.delete("/999")


def test_delete_norm_keeps_products(client):
    norm = NormFactory()
    product = StockProductFactory(norm=norm)

    assert client.delete(f"/{norm.pk}").status_code == 200

    product.refresh_from_db()
    assert product.norm is None
    assert not Norm.objects.exists()


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({}, ["CSN 021131", "DIN 84", "DIN 933", "ISO 1207"]),
        ({"type": "DIN"}, ["DIN 84", "DIN 933"]),
        ({"search_term": "93"}, ["DIN 933"]),
        ({"search_term": "din"}, ["DIN 84", "DIN 933"]),
        ({"search_term": "DIN 84"}, ["DIN 84"]),
        ({"search_term": "din_84"}, ["DIN 84"]),
        ({"search_term": "iso1207"}, ["ISO 1207"]),
        ({"search_term": "nothing"}, []),
        ({"search_term": "93", "type": "ISO"}, []),
    ],
)
def test_list_norms(client, params, expected):
    for norm_type, code in [
        ("DIN", "84"),
        ("DIN", "933"),
        ("ISO", "1207"),
        ("CSN", "021131"),
    ]:
        NormFactory(type=norm_type, code=code)

    response = client.get("/", query_params=params)

    assert [n["label"] for n in response.json()["data"]] == expected


def test_product_exposes_norm_with_aliases(products):
    iso = NormFactory(type=NormType.ISO, code="1207")
    din = NormFactory(type=NormType.DIN, code="84", equivalents=[iso])
    plain = StockProductFactory()
    linked = StockProductFactory(norm=din)

    listing = products.get("/").json()["data"]
    detail = products.get(f"/{linked.code}").json()["data"]

    by_code = {p["code"]: p for p in listing}
    assert by_code[plain.code]["norm"] is None
    assert by_code[linked.code]["norm"]["label"] == "DIN 84"
    assert [e["label"] for e in by_code[linked.code]["norm"]["equivalents"]] == [
        "ISO 1207"
    ]
    assert detail["norm"]["id"] == din.pk


def test_listing_norms_does_not_query_per_product(
    products, django_assert_max_num_queries
):
    din = NormFactory(equivalents=[NormFactory(type=NormType.ISO, code="1")])

    def measure(count: int) -> int:
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        for _ in range(count):
            StockProductFactory(norm=din)
        with CaptureQueriesContext(connection) as ctx:
            products.get("/")
        return len(ctx)

    assert measure(5) == measure(5)


def _product_body(**overrides):
    return {
        "name": "Screw",
        "code": "SCR-1",
        "type": "Component",
        "unit": "KS",
        **overrides,
    }


def test_create_and_update_product_with_norm(products):
    din = NormFactory()
    other = NormFactory(type=NormType.ISO, code="1")

    created = products.post("/", json=_product_body(norm_id=din.pk))
    assert created.status_code == 200
    assert created.json()["data"]["norm"]["id"] == din.pk

    updated = products.put("/SCR-1", json=_product_body(norm_id=other.pk))
    assert updated.json()["data"]["norm"]["label"] == "ISO 1"

    cleared = products.put("/SCR-1", json=_product_body(norm_id=None))
    assert cleared.json()["data"]["norm"] is None
    assert StockProduct.objects.get(code="SCR-1").norm is None


def test_product_with_unknown_norm_is_rejected(products):
    with pytest.raises(ApiBaseException, match="does not exist"):
        products.post("/", json=_product_body(norm_id=999999))

    assert not StockProduct.objects.exists()


# --- backfill job ---------------------------------------------------------------

BACKFILL = "/api/v1/norms/backfill"


@pytest.fixture
def http(user, celery_inline) -> Client:
    c = Client()
    c.force_login(user)
    return c


def test_backfill_requires_authentication(celery_inline):
    anonymous = Client()

    assert anonymous.post(BACKFILL).status_code == 401
    assert anonymous.get(f"{BACKFILL}/jobs/{uuid.uuid4()}").status_code == 401


def test_backfill_job_reports_result(http):
    p = StockProductFactory(
        attributes={"CUSTOMS_DECLARATION_GROUP": "7318", "a": "DIN 84", "b": "ISO 1"}
    )
    StockProductFactory(attributes={"a": "nonsense"}, code="BAD-1")

    started = http.post(BACKFILL)
    assert started.status_code == 202
    job_id = started.json()["data"]["job_id"]
    status = http.get(f"{BACKFILL}/jobs/{job_id}").json()["data"]

    assert status["state"] == "succeeded"
    assert status["percent"] == 100
    result = status["result"]
    assert result["products_scanned"] == 2
    assert result["customs_filled"] == 1
    assert result["norms_linked"] == 1
    assert result["aliases_linked"] == 1
    assert result["without_norm"] == 1
    assert result["invalid"] == [
        {
            "product_code": "BAD-1",
            "key": "a",
            "value": "nonsense",
            "reason": "no known norm (DIN / CSN / ISO) recognised",
        }
    ]
    p.refresh_from_db()
    assert p.norm.label == "DIN 84"


@pytest.mark.parametrize("job_id", ["nope", "123"])
def test_backfill_job_with_malformed_id(http, job_id):
    assert http.get(f"{BACKFILL}/jobs/{job_id}").status_code == 404


def test_backfill_unknown_job_is_pending(http):
    status = http.get(f"{BACKFILL}/jobs/{uuid.uuid4()}").json()["data"]

    assert status["state"] == "pending"
    assert status["result"] is None
