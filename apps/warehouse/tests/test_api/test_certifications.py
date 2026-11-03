from typing import Any

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja.testing import TestClient

from apps.warehouse.api.routes.certifications import routes as cert_routes
from apps.warehouse.api.routes.inbound_orders import routes as inbound_routes
from apps.warehouse.core.exceptions import ApiBaseException
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.warehouse import WarehouseOrderCreateSchema
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.models.warehouse import (
    Batch,
    Certification,
    InboundWarehouseOrderState,
    TrackingLevel,
    WarehouseItem,
)
from apps.warehouse.tests.factories.certification import CertificationFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import BatchFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def _pdf(name: str = "cert.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"%PDF-1.4 x", content_type="application/pdf")


def _attach(client: TestClient, order, item, **form: Any):
    files = form.pop("files", {"attachment": _pdf()})
    return client.post(
        f"/{order.code}/items/{item.index}/certification",
        data=form,
        FILES=files,
    )


# ── standalone CRUD ──────────────────────────────────────────────────────────


def test_create_certification_standalone(db) -> None:
    client = TestClient(cert_routes)

    res = client.post(
        "",
        data={"code": " EN-10204 ", "description": "3.1 cert"},
        FILES={"attachment": _pdf("mill.pdf")},
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"] == "EN-10204"
    assert data["description"] == "3.1 cert"
    assert data["attachment"]["name"] == "mill.pdf"
    assert data["batch_codes"] == []


def test_create_certification_without_description_or_file(db) -> None:
    res = TestClient(cert_routes).post("", data={"code": "ONLY-CODE"})

    assert res.status_code == 200
    assert res.json()["data"]["attachment"] is None
    assert res.json()["data"]["description"] is None


def test_certification_code_is_not_unique(db) -> None:
    client = TestClient(cert_routes)

    assert client.post("", data={"code": "DUP"}).status_code == 200
    assert client.post("", data={"code": "DUP"}).status_code == 200
    assert Certification.objects.filter(code="DUP").count() == 2


def test_create_certification_blank_code_rejected(db) -> None:
    with pytest.raises(ApiBaseException):
        TestClient(cert_routes).post("", data={"code": "   "})

    assert Certification.objects.count() == 0


def test_list_and_search_certifications(db) -> None:
    CertificationFactory.it(code="ALPHA", description="bolts")
    CertificationFactory.it(code="BETA", description="nuts")
    client = TestClient(cert_routes)

    assert len(client.get("").json()["data"]) == 2
    assert [c["code"] for c in client.get("?search_term=alp").json()["data"]] == [
        "ALPHA"
    ]
    assert [c["code"] for c in client.get("?search_term=NUTS").json()["data"]] == [
        "BETA"
    ]
    assert client.get("?search_term=zzz").json()["data"] == []


def test_update_certification_replaces_file(db) -> None:
    cert = CertificationFactory.it(code="OLD")
    old_name = cert.attachment.name

    res = TestClient(cert_routes).post(
        f"/{cert.pk}",
        data={"code": "NEW", "description": "d"},
        FILES={"attachment": _pdf("fresh.pdf")},
    )

    assert res.status_code == 200
    cert.refresh_from_db()
    assert cert.code == "NEW"
    assert cert.attachment.name != old_name
    assert "fresh" in str(cert.attachment.name)


def test_update_certification_keeps_file_when_not_supplied(db) -> None:
    cert = CertificationFactory.it()
    name = cert.attachment.name

    res = TestClient(cert_routes).post(f"/{cert.pk}", data={"code": "RENAMED"})

    assert res.status_code == 200
    cert.refresh_from_db()
    assert cert.attachment.name == name


def test_get_and_delete_certification(db) -> None:
    cert = CertificationFactory.it()
    client = TestClient(cert_routes)

    assert client.get(f"/{cert.pk}").json()["data"]["id"] == cert.pk
    assert client.delete(f"/{cert.pk}").status_code == 200
    assert not Certification.objects.filter(pk=cert.pk).exists()
    with pytest.raises(ObjectDoesNotExist):
        client.get(f"/{cert.pk}")


def test_delete_certification_with_stock_is_rejected(db) -> None:
    cert = CertificationFactory.it()
    batch = BatchFactory.it(certification=cert)
    WarehouseItemFactory.it(batch=batch, amount=5)

    with pytest.raises(ApiBaseException):
        TestClient(cert_routes).delete(f"/{cert.pk}")

    assert Certification.objects.filter(pk=cert.pk).exists()


def test_delete_certification_removes_unused_batches(db) -> None:
    cert = CertificationFactory.it()
    batch = BatchFactory.it(certification=cert)

    TestClient(cert_routes).delete(f"/{cert.pk}")

    assert not Batch.objects.filter(pk=batch.pk).exists()


# ── inbound order item binding ───────────────────────────────────────────────


def test_flag_item_as_certified_via_update(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order)

    res = client.put(
        f"/{order.code}/items/{item.index}",
        json={
            "product_code": item.stock_product.code,
            "product_name": item.stock_product.name,
            "amount": 3,
            "total_price": 30,
            "requires_certification": True,
        },
    )

    assert res.status_code == 200
    assert res.json()["data"]["requires_certification"] is True
    assert res.json()["data"]["certification"] is None


def test_attach_new_certification_creates_linked_batch(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)

    res = _attach(client, order, item, code="MILL-1", description="strength")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["certification"]["code"] == "MILL-1"
    assert data["certification"]["attachment"] is not None
    assert data["batch_code"]
    item.refresh_from_db()
    assert item.batch is not None
    assert item.batch.certification == item.certification
    assert data["certification"]["batch_codes"] == [data["batch_code"]]


@pytest.mark.parametrize(
    "form, files, flagged",
    [
        ({"code": "X"}, {}, True),  # file is mandatory for new certs
        ({"description": "no code"}, {"attachment": "pdf"}, True),
        ({"code": "X"}, {"attachment": "pdf"}, False),  # row not flagged
    ],
)
def test_attach_certification_invalid_input(db, form, files, flagged) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=flagged)
    files = {k: _pdf() for k in files}

    with pytest.raises(ApiBaseException):
        client.post(
            f"/{order.code}/items/{item.index}/certification", data=form, FILES=files
        )

    item.refresh_from_db()
    assert item.certification is None
    assert item.batch is None
    assert Certification.objects.count() == 0


def test_attach_existing_certification_creates_new_batch_each_time(db) -> None:
    client = TestClient(inbound_routes)
    cert = CertificationFactory.it()
    order = InboundOrderFactory.it()
    first = InboundOrderItemFactory.it(order=order, requires_certification=True)
    second = InboundOrderItemFactory.it(order=order, requires_certification=True)

    for item in (first, second):
        res = client.post(
            f"/{order.code}/items/{item.index}/certification",
            data={"certification_id": cert.pk},
        )
        assert res.status_code == 200

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.batch != second.batch
    assert cert.batches.count() == 2
    assert Certification.objects.count() == 1


def test_attach_unknown_certification_404(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)

    with pytest.raises(ObjectDoesNotExist):
        client.post(
            f"/{order.code}/items/{item.index}/certification",
            data={"certification_id": 99999},
        )


def test_replacing_certification_drops_previous_batch(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)
    _attach(client, order, item, code="A")
    item.refresh_from_db()
    old_batch_id = item.batch_id
    assert old_batch_id is not None

    _attach(client, order, item, code="B")

    item.refresh_from_db()
    assert item.certification.code == "B"  # type: ignore[union-attr]
    assert item.batch_id != old_batch_id
    assert not Batch.objects.filter(pk=old_batch_id).exists()


def test_remove_certification_from_item(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)
    _attach(client, order, item, code="A")

    res = client.delete(f"/{order.code}/items/{item.index}/certification")

    assert res.status_code == 200
    assert res.json()["data"]["certification"] is None
    assert res.json()["data"]["batch_code"] is None
    assert Batch.objects.count() == 0
    assert Certification.objects.count() == 1  # standalone cert survives


def test_unflagging_item_detaches_certification(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)
    _attach(client, order, item, code="A")

    res = client.put(
        f"/{order.code}/items/{item.index}",
        json={
            "product_code": item.stock_product.code,
            "product_name": item.stock_product.name,
            "amount": 1,
            "total_price": 1,
            "requires_certification": False,
        },
    )

    assert res.status_code == 200
    item.refresh_from_db()
    assert item.certification is None
    assert item.batch is None
    assert Batch.objects.count() == 0


def test_removing_item_deletes_its_batch(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)
    _attach(client, order, item, code="A")

    res = client.delete(f"/{order.code}/items/{item.index}")

    assert res.status_code == 200
    assert Batch.objects.count() == 0


def test_certification_locked_once_order_not_editable(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it(state=InboundOrderState.RECEIVING)
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)

    with pytest.raises(ApiBaseException):
        _attach(client, order, item, code="A")

    assert Certification.objects.count() == 0


# ── submit gate ──────────────────────────────────────────────────────────────


def _transition(client: TestClient, order):
    return client.post(f"/{order.code}/transition", json={"action": "next"})


def test_submit_blocked_until_certified_rows_have_certification(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    plain = InboundOrderItemFactory.it(order=order)
    certified = InboundOrderItemFactory.it(order=order, requires_certification=True)
    assert plain.requires_certification is False

    with pytest.raises(ApiBaseException):
        _transition(client, order)

    order.refresh_from_db()
    assert order.state == InboundOrderState.DRAFT

    _attach(client, order, certified, code="OK")
    ok = _transition(client, order)

    assert ok.status_code == 200
    order.refresh_from_db()
    assert order.state == InboundOrderState.SUBMITTED


def test_submit_without_flagged_rows_unaffected(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    InboundOrderItemFactory.it(order=order)

    assert _transition(client, order).status_code == 200


def test_duplicate_keeps_flag_but_not_certification(db) -> None:
    client = TestClient(inbound_routes)
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order, requires_certification=True)
    _attach(client, order, item, code="A")

    res = client.post(f"/{order.code}/duplicate")

    assert res.status_code == 200
    new_item = res.json()["data"]["items"][0]
    assert new_item["requires_certification"] is True
    assert new_item["certification"] is None
    assert new_item["batch_code"] is None


# ── warehouse receipt pre-fill ───────────────────────────────────────────────


def test_warehouse_order_prefills_batch_for_certified_rows(db) -> None:
    client = TestClient(inbound_routes)
    context = RequestContext(username="x", user_id=None)
    putaway = WarehouseLocationFactory.it(is_putaway=True)
    order = InboundOrderFactory.it()
    plain = InboundOrderItemFactory.it(order=order)
    certified = InboundOrderItemFactory.it(order=order, requires_certification=True)
    batch_code = _attach(client, order, certified, code="A").json()["data"][
        "batch_code"
    ]

    w_order = warehouse_service.create_inbound_order(
        WarehouseOrderCreateSchema(purchase_order_code=order.code), context=context
    )
    warehouse_service.confirm_arrival(w_order.code, putaway.code, context=context)

    from apps.warehouse.models.warehouse import InboundWarehouseOrderItem

    rows = {
        r.stock_product_id: r
        for r in InboundWarehouseOrderItem.objects.filter(
            warehouse_order__code=w_order.code
        )
    }
    assert rows[certified.stock_product_id].tracking_level == TrackingLevel.FUNGIBLE
    assert rows[certified.stock_product_id].batch_barcode == batch_code
    assert rows[plain.stock_product_id].tracking_level == TrackingLevel.FUNGIBLE
    assert rows[plain.stock_product_id].batch_barcode is None


# ── outbound picker ──────────────────────────────────────────────────────────


def _stock(product, batch, amount, state=InboundWarehouseOrderState.COMPLETED):
    return WarehouseItemFactory.it(
        stock_product=product,
        batch=batch,
        amount=amount,
        tracking_level=TrackingLevel.BATCH,
        order_in=InboundWarehouseOrderFactory.it(state=state),
        location=WarehouseLocationFactory.it(is_putaway=False),
    )


def _batch_with_barcode(cert, code):
    batch = BatchFactory.it(certification=cert)
    batch.attach_barcode(code, is_primary=True)
    return batch


def test_available_certifications_one_row_per_batch(db) -> None:
    """
    A requirement points at a single batch, so every row's amount has to be
    exactly what that batch can deliver - batches are never summed together.
    """
    product = StockProductFactory.it()
    cert = CertificationFactory.it(code="C1")
    small = _batch_with_barcode(cert, "BAT-SMALL")
    big = _batch_with_barcode(cert, "BAT-BIG")
    _stock(product, small, 3)
    _stock(product, big, 7)
    _stock(product, big, 1)

    res = TestClient(cert_routes).get(f"/available?product_code={product.code}")

    assert res.status_code == 200
    rows = {r["batch_code"]: r for r in res.json()["data"]}
    assert set(rows) == {"BAT-SMALL", "BAT-BIG"}
    assert rows["BAT-SMALL"]["amount"] == 3
    assert rows["BAT-BIG"]["amount"] == 8
    assert all(r["id"] == cert.pk and r["code"] == "C1" for r in rows.values())
    assert rows["BAT-BIG"]["attachment"]["url"]


def test_available_certifications_ignores_other_products_uncertified_and_unavailable(
    db,
) -> None:
    product = StockProductFactory.it()
    other = StockProductFactory.it()
    cert = CertificationFactory.it()
    batch = _batch_with_barcode(cert, "BAT-1")
    _stock(other, batch, 5)  # different product
    _stock(product, BatchFactory.it(), 5)  # batch without certification
    _stock(product, batch, 5, state=InboundWarehouseOrderState.DRAFT)  # not received
    _stock(product, batch, 0)  # empty

    res = TestClient(cert_routes).get(f"/available?product_code={product.code}")

    assert res.json()["data"] == []


@pytest.mark.parametrize(
    "state, expected",
    [
        (InboundWarehouseOrderState.PENDING, True),  # confirmed, still to be put away
        (InboundWarehouseOrderState.STARTED, True),
        (InboundWarehouseOrderState.COMPLETED, True),
        (InboundWarehouseOrderState.DRAFT, False),  # not confirmed yet
        (InboundWarehouseOrderState.IN_TRANSIT, False),
    ],
)
def test_available_certifications_in_receiving_location(db, state, expected) -> None:
    """Confirmed goods are available right away - even before they reach a shelf."""
    product = StockProductFactory.it()
    batch = _batch_with_barcode(CertificationFactory.it(), "BAT-1")
    WarehouseItemFactory.it(
        stock_product=product,
        batch=batch,
        amount=5,
        tracking_level=TrackingLevel.BATCH,
        order_in=InboundWarehouseOrderFactory.it(state=state),
        location=WarehouseLocationFactory.it(is_putaway=True),
    )

    rows = (
        TestClient(cert_routes)
        .get(f"/available?product_code={product.code}")
        .json()["data"]
    )

    assert [r["amount"] for r in rows] == ([5] if expected else [])


def test_available_stock_matches_physical_stock_for_confirmed_goods(db) -> None:
    """One rule everywhere: all physically held goods, minus those already assigned."""
    product = StockProductFactory.it()
    confirmed = InboundWarehouseOrderFactory.it(
        state=InboundWarehouseOrderState.PENDING
    )
    for is_putaway in (True, False):
        WarehouseItemFactory.it(
            stock_product=product,
            amount=2,
            order_in=confirmed,
            location=WarehouseLocationFactory.it(is_putaway=is_putaway),
        )

    assert WarehouseItem.available.total_amount(product.code) == 4
    assert WarehouseItem.physical_stock.total_amount(product.code) == 4


# ── reverse view ─────────────────────────────────────────────────────────────


def test_certification_items_lists_stock_of_all_its_batches(db) -> None:
    product = StockProductFactory.it()
    other_product = StockProductFactory.it()
    cert = CertificationFactory.it()
    other_cert = CertificationFactory.it()
    batch_a = _batch_with_barcode(cert, "BAT-A")
    batch_b = _batch_with_barcode(cert, "BAT-B")
    wanted = [_stock(product, batch_a, 4), _stock(other_product, batch_b, 6)]
    _stock(product, _batch_with_barcode(other_cert, "BAT-X"), 9)  # other cert
    _stock(product, BatchFactory.it(), 9)  # no certification at all

    res = TestClient(cert_routes).get(f"/{cert.pk}/items")

    assert res.status_code == 200
    data = res.json()["data"]
    assert sorted(i["id"] for i in data) == sorted(i.pk for i in wanted)
    by_batch = {i["batch"]["primary_barcode"]["code"]: i for i in data}
    assert by_batch["BAT-A"]["amount"] == 4
    assert by_batch["BAT-A"]["batch"]["certification"] == {
        "id": cert.pk,
        "code": cert.code,
    }


def test_certification_items_empty_and_unknown(db) -> None:
    cert = CertificationFactory.it()
    client = TestClient(cert_routes)

    assert client.get(f"/{cert.pk}/items").json()["data"] == []
    with pytest.raises(ObjectDoesNotExist):
        client.get("/99999/items")


def test_certification_items_skips_goods_already_picked(db) -> None:
    cert = CertificationFactory.it()
    batch = _batch_with_barcode(cert, "BAT-1")
    product = StockProductFactory.it()
    kept = _stock(product, batch, 3)
    picked = _stock(product, batch, 5)
    outbound_order = OutboundOrderFactory.it()
    source = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=5
    )
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=WarehouseOrderOutFactory.it(order=outbound_order),
        source_order_item=source,
        stock_product=product,
        warehouse_item=picked,
        amount=5,
    )

    ids = [
        i["id"] for i in TestClient(cert_routes).get(f"/{cert.pk}/items").json()["data"]
    ]

    assert ids == [kept.pk]


def test_batch_of_warehouse_item_exposes_its_certification(db) -> None:
    from apps.warehouse.core.transformation import warehouse_item_orm_to_schema

    cert = CertificationFactory.it(code="EN-10204")
    item = _stock(StockProductFactory.it(), _batch_with_barcode(cert, "BAT-1"), 1)
    plain = _stock(StockProductFactory.it(), BatchFactory.it(), 1)

    assert warehouse_item_orm_to_schema(item).batch.certification.code == "EN-10204"  # type: ignore[union-attr]
    assert warehouse_item_orm_to_schema(plain).batch.certification is None  # type: ignore[union-attr]


def test_available_certifications_unknown_product_is_empty(db) -> None:
    res = TestClient(cert_routes).get("/available?product_code=NOPE")

    assert res.status_code == 200
    assert res.json()["data"] == []


def test_available_certifications_ordered_date_from_inbound_order(db) -> None:
    product = StockProductFactory.it()
    cert = CertificationFactory.it()
    batch = _batch_with_barcode(cert, "BAT-1")
    order = InboundOrderFactory.it()
    InboundOrderItemFactory.it(
        order=order, certification=cert, batch=batch, requires_certification=True
    )
    _stock(product, batch, 2)

    (row,) = (
        TestClient(cert_routes)
        .get(f"/available?product_code={product.code}")
        .json()["data"]
    )

    assert row["ordered_date"].startswith(order.created.date().isoformat())
