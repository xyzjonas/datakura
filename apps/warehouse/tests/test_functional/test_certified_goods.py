"""
End-to-end: certified goods are bought (inbound), received, put away and then
sold again (outbound) by requiring the certification.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja.testing import TestClient

from apps.warehouse.api.routes.certifications import routes as cert_routes
from apps.warehouse.api.routes.inbound_orders import routes as order_routes
from apps.warehouse.api.routes.outbound_orders import routes as outbound_routes
from apps.warehouse.api.routes.packaging import routes as packaging_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.exceptions import ApiBaseException
from apps.warehouse.core.schemas.orders import InboundOrderCreateOrUpdateSchema
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    WarehouseItem,
)
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    StockProductFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


@pytest.fixture
def order_client() -> TestClient:
    return TestClient(order_routes)


@pytest.fixture
def warehouse_client() -> TestClient:
    return TestClient(warehouse_routes)


@pytest.fixture
def cert_client() -> TestClient:
    return TestClient(cert_routes)


def _buy_certified(
    order_client: TestClient, supplier, product, cert_code: str, amount: int = 100
) -> tuple[str, str]:
    """Create + certify + submit a purchase order. Returns (order code, batch code)."""
    res = order_client.post(
        "/",
        json=InboundOrderCreateOrUpdateSchema(
            supplier_code=supplier.code,
            supplier_name=supplier.name,
            currency="CZK",
        ).model_dump(),
    )
    assert res.status_code == 200
    order_code = res.json()["data"]["code"]

    res = order_client.post(
        f"/{order_code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": amount,
            "total_price": amount * 10,
            "requires_certification": True,
        },
    )
    assert res.status_code == 200
    index = res.json()["data"]["index"]

    res = order_client.post(
        f"/{order_code}/items/{index}/certification",
        data={"code": cert_code, "description": "material strength"},
        FILES={
            "attachment": SimpleUploadedFile(
                "iso.pdf", b"%PDF-1.4 iso", content_type="application/pdf"
            )
        },
    )
    assert res.status_code == 200
    batch_code = res.json()["data"]["batch_code"]
    assert batch_code

    res = order_client.post(f"/{order_code}/transition", json={"action": "next"})
    assert res.status_code == 200
    return order_code, batch_code


def _receive_and_put_away(
    warehouse_client: TestClient,
    order_code: str,
    receiving,
    storage,
    track=None,
    put_away: bool = True,
) -> str:
    res = warehouse_client.post(
        "/orders-incoming", json={"purchase_order_code": order_code}
    )
    assert res.status_code == 200
    w_code = res.json()["data"]["code"]

    res = warehouse_client.post(
        f"/orders-incoming/{w_code}/transition",
        json={"location_code": receiving.code},
    )
    assert res.status_code == 200
    order_items = res.json()["data"]["order_items"]

    if track:
        track(w_code, order_items[0])

    res = warehouse_client.post(f"/orders-incoming/{w_code}/transition", json={})
    assert res.status_code == 200

    if not put_away:
        return w_code

    for item in InboundWarehouseOrder.objects.get(code=w_code).items.all():
        res = warehouse_client.post(
            f"/orders-incoming/{w_code}/items/{item.id}/putaway",
            json={"new_location_code": storage.code},
        )
        assert res.status_code == 200
    assert (
        InboundWarehouseOrder.objects.get(code=w_code).state
        == InboundWarehouseOrderState.COMPLETED
    )
    return w_code


def test_certified_goods_are_found_by_the_outbound_picker(
    db, order_client, warehouse_client, cert_client
):
    supplier = CustomerFactory()
    product = StockProductFactory()
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)

    order_code, batch_code = _buy_certified(order_client, supplier, product, "ISO-9001")
    _receive_and_put_away(warehouse_client, order_code, receiving, storage)

    stock = WarehouseItem.objects.filter(stock_product=product)
    assert stock.count() == 1
    assert stock.get().batch.certification.code == "ISO-9001"

    res = cert_client.get(f"/available?product_code={product.code}")

    assert res.status_code == 200
    (row,) = res.json()["data"]
    assert row["code"] == "ISO-9001"
    assert row["amount"] == 100
    assert row["batch_code"] == batch_code


def test_certified_goods_tracked_as_packages_are_found_by_the_picker(
    db, order_client, warehouse_client, cert_client
):
    supplier = CustomerFactory()
    product = StockProductFactory(unit_of_measure__name="KS")
    package_type = PackageTypeFactory(
        name="BAG-10", amount=10, unit_of_measure=product.unit_of_measure
    )
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)

    order_code, batch_code = _buy_certified(order_client, supplier, product, "ISO-PKG")

    def track(w_code, order_item):
        # what the UI does: the locked, pre-filled batch is sent along
        batch = WarehouseItem  # placeholder to keep linters quiet
        del batch
        from apps.warehouse.core.services.batches import batches_service
        from apps.warehouse.models.warehouse import Batch

        batch_model = next(
            b
            for b in Batch.objects.filter(certification__isnull=False)
            if b.get_primary_barcode().code == batch_code
        )
        batch_schema = batches_service.batch_orm_to_schema(batch_model).model_dump(
            mode="json"
        )
        res = TestClient(packaging_routes).post(
            "/preview-package",
            json={
                "order_item_id": order_item["id"],
                "product_code": product.code,
                "package_name": package_type.name,
                "amount": 100,
            },
        )
        assert res.status_code == 200
        to_add = res.json()["data"]
        for item in to_add:
            item["batch"] = batch_schema
        res = warehouse_client.post(
            f"/orders-incoming/{w_code}/order-items/{order_item['id']}/track",
            json={"to_be_added": to_add},
        )
        assert res.status_code == 200

    _receive_and_put_away(warehouse_client, order_code, receiving, storage, track)

    assert WarehouseItem.objects.filter(stock_product=product).count() == 10
    res = cert_client.get(f"/available?product_code={product.code}")

    (row,) = res.json()["data"]
    assert row["code"] == "ISO-PKG"
    assert row["amount"] == 100
    assert row["batch_code"] == batch_code


def test_tracking_cannot_drop_the_certified_batch(
    db, order_client, warehouse_client, cert_client
):
    """
    The UI pre-fills and locks the batch, but if that ever fails (slow lookup,
    stale client) the tracked rows must still end up in the certified batch.
    """
    supplier = CustomerFactory()
    product = StockProductFactory(unit_of_measure__name="KS")
    package_type = PackageTypeFactory(
        name="BAG-10", amount=10, unit_of_measure=product.unit_of_measure
    )
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)
    order_code, batch_code = _buy_certified(order_client, supplier, product, "ISO-LOCK")

    def track_without_batch(w_code, order_item):
        res = TestClient(packaging_routes).post(
            "/preview-package",
            json={
                "order_item_id": order_item["id"],
                "product_code": product.code,
                "package_name": package_type.name,
                "amount": 100,
            },
        )
        to_add = res.json()["data"]
        assert all(item["batch"] is None for item in to_add)
        res = warehouse_client.post(
            f"/orders-incoming/{w_code}/order-items/{order_item['id']}/track",
            json={"to_be_added": to_add},
        )
        assert res.status_code == 200

    _receive_and_put_away(
        warehouse_client, order_code, receiving, storage, track_without_batch
    )

    assert not WarehouseItem.objects.filter(
        stock_product=product, batch__isnull=True
    ).exists()
    (row,) = cert_client.get(f"/available?product_code={product.code}").json()["data"]
    assert row["amount"] == 100
    assert row["batch_code"] == batch_code


def test_sell_the_goods_of_a_given_iso_certification(
    db, order_client, warehouse_client, cert_client
):
    """
    Buy certified goods, receive them, then sell 30 pcs requiring that exact
    certification while uncertified stock of the same product is around.
    """
    supplier = CustomerFactory()
    customer = CustomerFactory()
    product = StockProductFactory()
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)

    order_code, batch_code = _buy_certified(order_client, supplier, product, "ISO-9001")
    _receive_and_put_away(warehouse_client, order_code, receiving, storage)

    # decoy: older, uncertified stock of the very same product
    plain_order = InboundOrderFactory.it()
    decoy = WarehouseItemFactory.it(
        stock_product=product,
        amount=500,
        location=storage,
        batch=None,
        order_in=InboundWarehouseOrderFactory.it(
            order=plain_order, state=InboundWarehouseOrderState.COMPLETED
        ),
    )

    # 1. the picker offers the certification
    (row,) = cert_client.get(f"/available?product_code={product.code}").json()["data"]
    assert row["code"] == "ISO-9001"
    assert row["amount"] == 100  # the decoy is not counted

    # 2. place the OP order, requiring the certified batch the picker returned
    outbound_client = TestClient(outbound_routes)
    res = outbound_client.post(
        "/",
        json={
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
        },
    )
    assert res.status_code == 200
    op_code = res.json()["data"]["code"]
    res = outbound_client.post(
        f"/{op_code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 30,
            "total_price": 600,
            "desired_batch_code": row["batch_code"],
        },
    )
    assert res.status_code == 200
    assert res.json()["data"]["desired_batch_code"] == batch_code

    res = outbound_client.post(f"/{op_code}/transition", json={"action": "next"})
    assert res.status_code == 200

    # 3. the warehouse requirement only offers the certified stock
    w_order = OutboundWarehouseOrder.objects.get(order__code=op_code)
    requirement = w_order.order_items.get()
    assert requirement.desired_batch.get_primary_barcode().code == batch_code
    res = warehouse_client.get(
        f"/orders-outgoing/{w_order.code}/order-items/{requirement.pk}/candidates"
    )
    assert res.status_code == 200
    candidates = res.json()["data"]
    assert len(candidates) == 1
    assert candidates[0]["batch"]["primary_barcode"]["code"] == batch_code
    assert candidates[0]["id"] != decoy.pk

    # 4. the decoy can not be assigned, the certified item can
    certified_item = WarehouseItem.objects.get(pk=candidates[0]["id"])
    with pytest.raises(ApiBaseException):
        warehouse_client.post(
            f"/orders-outgoing/{w_order.code}/order-items/{requirement.pk}/assign",
            json={"warehouse_item_id": decoy.pk, "amount": 30},
        )
    res = warehouse_client.post(
        f"/orders-outgoing/{w_order.code}/order-items/{requirement.pk}/assign",
        json={"warehouse_item_id": certified_item.pk, "amount": 30},
    )
    assert res.status_code == 200
    certified_item.refresh_from_db()
    assert certified_item.batch.certification.code == "ISO-9001"

    # 5. what is left of the certification
    (row,) = cert_client.get(f"/available?product_code={product.code}").json()["data"]
    assert row["amount"] == 70


def test_confirmed_goods_are_sellable_before_put_away(
    db, order_client, warehouse_client, cert_client
):
    """Goods are available as soon as the receipt is confirmed - no shelf needed."""
    supplier = CustomerFactory()
    customer = CustomerFactory()
    product = StockProductFactory()
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)
    order_code, batch_code = _buy_certified(order_client, supplier, product, "ISO-9001")
    _receive_and_put_away(
        warehouse_client, order_code, receiving, storage, put_away=False
    )

    item = WarehouseItem.objects.get(stock_product=product)
    assert item.location == receiving  # still in the receiving location

    (row,) = cert_client.get(f"/available?product_code={product.code}").json()["data"]
    assert row["amount"] == 100
    assert row["batch_code"] == batch_code

    outbound_client = TestClient(outbound_routes)
    op_code = outbound_client.post(
        "/",
        json={
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
        },
    ).json()["data"]["code"]
    outbound_client.post(
        f"/{op_code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 25,
            "total_price": 500,
            "desired_batch_code": row["batch_code"],
        },
    )
    outbound_client.post(f"/{op_code}/transition", json={"action": "next"})

    w_order = OutboundWarehouseOrder.objects.get(order__code=op_code)
    requirement = w_order.order_items.get()
    res = warehouse_client.get(
        f"/orders-outgoing/{w_order.code}/order-items/{requirement.pk}/candidates"
    )
    assert [c["id"] for c in res.json()["data"]] == [item.pk]
