"""
Manufacturing order item requirements (batch / package / origin country),
their enforcement when picking and the batch inheritance of produced goods.
"""

from decimal import Decimal
from typing import Any

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.manufacturing_orders import routes as mfg_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    WarehouseItemBadRequestError,
    WarehouseOrderNotEditableError,
)
from apps.warehouse.core.services.manufacturing import manufacturing_orders_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.manufacturing import (
    ManufacturingOrderItem,
    ManufacturingOrderState,
)
from apps.warehouse.models.warehouse import (
    Batch,
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.certification import CertificationFactory
from apps.warehouse.tests.factories.manufacturing import (
    ManufacturingOrderFactory,
    ManufacturingOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import BatchFactory, PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)


@pytest.fixture
def mfg_client() -> TestClient:
    return TestClient(mfg_routes)


@pytest.fixture
def wh_client() -> TestClient:
    return TestClient(warehouse_routes)


def _batch(code: str, certified: bool = False) -> Batch:
    batch = BatchFactory.it(certification=CertificationFactory() if certified else None)
    batch.attach_barcode(code, is_primary=True)
    return batch


def _item_payload(**extra: Any) -> dict[str, Any]:
    in_product = StockProductFactory.it()
    out_product = StockProductFactory.it()
    return {
        "in_product_code": in_product.code,
        "in_product_name": in_product.name,
        "in_amount": 2,
        "out_product_code": out_product.code,
        "out_product_name": out_product.name,
        "out_amount": 4,
        **extra,
    }


# ---------------------------------------------------------------- item CRUD


def test_add_item_stores_requirements(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)
    batch = _batch("BATCH-CERT-1", certified=True)

    res = mfg_client.post(
        f"/{order.code}/items",
        json=_item_payload(
            desired_batch_code="BATCH-CERT-1", required_origin_country="de"
        ),
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["desired_batch_code"] == "BATCH-CERT-1"
    assert data["desired_batch_certification"]["id"] == batch.certification_id
    assert data["required_origin_country"] == "DE"
    stored = ManufacturingOrderItem.objects.get(order=order)
    assert stored.desired_batch == batch
    assert stored.required_origin_country == "DE"


def test_add_item_without_requirements_has_none(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)

    res = mfg_client.post(f"/{order.code}/items", json=_item_payload())

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["desired_batch_code"] is None
    assert data["desired_package_type_name"] is None
    assert data["required_origin_country"] is None


def test_add_item_with_unconvertible_package_type_is_rejected(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)
    package = PackageTypeFactory(name="B0100")  # unit differs from the product's

    with pytest.raises(WarehouseItemBadRequestError):
        mfg_client.post(
            f"/{order.code}/items",
            json=_item_payload(desired_package_type_name=package.name),
        )

    assert not ManufacturingOrderItem.objects.filter(order=order).exists()


@pytest.mark.parametrize("country", ["XX", "CZE", "UK"])
def test_add_item_rejects_invalid_origin_country(db, mfg_client, country) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)

    res = mfg_client.post(
        f"/{order.code}/items", json=_item_payload(required_origin_country=country)
    )

    assert res.status_code == 422
    assert not ManufacturingOrderItem.objects.filter(order=order).exists()


def test_add_item_rejects_unknown_batch(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)

    with pytest.raises(WarehouseItemBadRequestError):
        mfg_client.post(
            f"/{order.code}/items", json=_item_payload(desired_batch_code="NOPE")
        )

    assert not ManufacturingOrderItem.objects.filter(order=order).exists()


def test_update_item_changes_and_clears_requirements(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)
    batch = _batch("BATCH-U-1")
    item = ManufacturingOrderItemFactory.it(order=order, desired_batch=batch)
    payload = {
        "in_product_code": item.in_product.code,
        "in_product_name": item.in_product.name,
        "in_amount": 1,
        "out_product_code": item.out_product.code,
        "out_product_name": item.out_product.name,
        "out_amount": 1,
    }

    res = mfg_client.put(f"/{order.code}/items/{item.pk}", json=payload)

    assert res.status_code == 200
    item.refresh_from_db()
    assert item.desired_batch is None

    res = mfg_client.put(
        f"/{order.code}/items/{item.pk}",
        json={
            **payload,
            "desired_batch_code": "BATCH-U-1",
            "required_origin_country": "CN",
        },
    )
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.desired_batch == batch
    assert item.required_origin_country == "CN"


def test_requirements_cannot_change_after_confirmation(db, mfg_client) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.CONFIRMED)

    with pytest.raises(WarehouseOrderNotEditableError):
        mfg_client.post(
            f"/{order.code}/items", json=_item_payload(required_origin_country="DE")
        )

    assert not ManufacturingOrderItem.objects.filter(order=order).exists()


# ------------------------------------------------- outbound warehouse order


def test_confirmation_copies_requirements_to_outbound_items(db, context) -> None:
    order = ManufacturingOrderFactory.it(state=ManufacturingOrderState.DRAFT)
    batch = _batch("BATCH-O-1")
    item = ManufacturingOrderItemFactory.it(
        order=order, desired_batch=batch, required_origin_country="DE"
    )

    manufacturing_orders_service.transition_order(order.code, context)

    outbound = OutboundWarehouseOrderItem.objects.get(
        warehouse_order__manufacturing_order=order
    )
    assert outbound.source_manufacturing_item == item
    assert outbound.desired_batch == batch
    assert outbound.required_origin_country == "DE"


def _pending_mfg_outbound(
    mfg_item, amount: Decimal | int = 4
) -> OutboundWarehouseOrderItem:
    warehouse_order = WarehouseOrderOutFactory.it(
        order=None,
        manufacturing_order=mfg_item.order,
        state=OutboundWarehouseOrderState.PENDING,
    )
    return OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=None,
        source_manufacturing_item=mfg_item,
        stock_product=mfg_item.in_product,
        amount=amount,
        desired_batch=mfg_item.desired_batch,
        desired_package_type=mfg_item.desired_package_type,
    )


def _stock(product, amount, batch=None):
    return WarehouseItemFactory.it(
        order_in=InboundWarehouseOrderFactory.it(
            state=InboundWarehouseOrderState.PENDING
        ),
        stock_product=product,
        amount=amount,
        location=WarehouseLocationFactory.it(is_putaway=False),
        batch=batch,
    )


def test_picking_wrong_batch_is_rejected(db, wh_client) -> None:
    required = _batch("BATCH-REQ")
    other = _batch("BATCH-OTHER")
    mfg_item = ManufacturingOrderItemFactory.it(desired_batch=required)
    requirement = _pending_mfg_outbound(mfg_item)
    wrong = _stock(mfg_item.in_product, 4, batch=other)
    batchless = _stock(mfg_item.in_product, 4)

    for stock in (wrong, batchless):
        with pytest.raises(WarehouseGenericError, match="does not match"):
            wh_client.post(
                f"/orders-outgoing/{requirement.warehouse_order.code}/order-items/{requirement.pk}/assign",
                json={"warehouse_item_id": stock.pk},
            )

    requirement.refresh_from_db()
    assert requirement.warehouse_item is None


def test_picking_required_batch_is_accepted(db, wh_client) -> None:
    required = _batch("BATCH-REQ")
    mfg_item = ManufacturingOrderItemFactory.it(desired_batch=required)
    requirement = _pending_mfg_outbound(mfg_item)
    good = _stock(mfg_item.in_product, 4, batch=required)

    res = wh_client.post(
        f"/orders-outgoing/{requirement.warehouse_order.code}/order-items/{requirement.pk}/assign",
        json={"warehouse_item_id": good.pk},
    )

    assert res.status_code == 200


def test_partial_pick_keeps_manufacturing_item_link(db, wh_client) -> None:
    """Split-off rows must stay linked, otherwise cost/batch tracing is lost."""
    mfg_item = ManufacturingOrderItemFactory.it()
    requirement = _pending_mfg_outbound(mfg_item, amount=4)
    stock = _stock(mfg_item.in_product, 4)

    res = wh_client.post(
        f"/orders-outgoing/{requirement.warehouse_order.code}/order-items/{requirement.pk}/assign",
        json={"warehouse_item_id": stock.pk, "amount": 1},
    )

    assert res.status_code == 200
    rows = OutboundWarehouseOrderItem.objects.filter(
        warehouse_order=requirement.warehouse_order
    )
    assert rows.count() == 2
    assert all(r.source_manufacturing_item_id == mfg_item.pk for r in rows)


def test_offload_split_keeps_manufacturing_item_link(db, wh_client) -> None:
    mfg_item = ManufacturingOrderItemFactory.it()
    requirement = _pending_mfg_outbound(mfg_item, amount=4)

    res = wh_client.post(
        f"/orders-outgoing/{requirement.warehouse_order.code}/offload",
        json={"items": [{"item_id": requirement.pk, "amount": 1}]},
    )

    assert res.status_code == 200
    rows = OutboundWarehouseOrderItem.objects.filter(
        warehouse_order__manufacturing_order=mfg_item.order
    )
    assert rows.count() == 2
    assert all(r.source_manufacturing_item_id == mfg_item.pk for r in rows)


# ------------------------------------------------------ batch inheritance


def _picked(mfg_item, batch, amount=1) -> None:
    warehouse_order = (
        OutboundWarehouseOrder.objects.filter(manufacturing_order=mfg_item.order)
        .order_by("pk")
        .first()
    ) or WarehouseOrderOutFactory.it(
        order=None,
        manufacturing_order=mfg_item.order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=None,
        source_manufacturing_item=mfg_item,
        stock_product=mfg_item.in_product,
        amount=amount,
        warehouse_item=_stock(mfg_item.in_product, amount, batch=batch),
    )


def _arrive(mfg_order, context) -> list[InboundWarehouseOrderItem]:
    location = WarehouseLocationFactory.it(is_putaway=True)
    inbound = InboundWarehouseOrderFactory.it(
        order=None,
        manufacturing_order=mfg_order,
        state=InboundWarehouseOrderState.IN_TRANSIT,
        pickup_location=location,
    )
    warehouse_service.confirm_arrival(inbound.code, location.code, context=context)
    return list(InboundWarehouseOrderItem.objects.filter(warehouse_order=inbound))


def test_produced_goods_inherit_picked_batch(db, context) -> None:
    batch = _batch("BATCH-CERT-X", certified=True)
    mfg_item = ManufacturingOrderItemFactory.it()
    _picked(mfg_item, batch)

    (out_item,) = _arrive(mfg_item.order, context)

    assert out_item.batch_barcode == "BATCH-CERT-X"


def test_produced_goods_inherit_batch_picked_in_several_chunks(db, context) -> None:
    batch = _batch("BATCH-CHUNKS")
    mfg_item = ManufacturingOrderItemFactory.it()
    _picked(mfg_item, batch)
    _picked(mfg_item, batch)

    (out_item,) = _arrive(mfg_item.order, context)

    assert out_item.batch_barcode == "BATCH-CHUNKS"


@pytest.mark.parametrize(
    "picks",
    [
        pytest.param([], id="nothing-picked"),
        pytest.param([None], id="batchless-pick"),
        pytest.param(["A", "B"], id="mixed-batches"),
        pytest.param(["A", None], id="batch-and-batchless"),
    ],
)
def test_produced_goods_get_no_batch_when_ambiguous(db, context, picks) -> None:
    mfg_item = ManufacturingOrderItemFactory.it()
    for pick in picks:
        _picked(mfg_item, _batch(f"BATCH-{pick}") if pick else None)

    (out_item,) = _arrive(mfg_item.order, context)

    assert out_item.batch_barcode is None


def test_batch_is_inherited_per_item(db, context) -> None:
    order = ManufacturingOrderFactory.it()
    certified = ManufacturingOrderItemFactory.it(order=order, index=0)
    plain = ManufacturingOrderItemFactory.it(order=order, index=1)
    _picked(certified, _batch("BATCH-ONLY-FIRST", certified=True))
    _picked(plain, None)

    items = {i.index: i for i in _arrive(order, context)}

    assert items[0].batch_barcode == "BATCH-ONLY-FIRST"
    assert items[1].batch_barcode is None


def test_confirmed_inbound_creates_items_with_inherited_batch(db, context) -> None:
    batch = _batch("BATCH-FULL")
    mfg_item = ManufacturingOrderItemFactory.it()
    _picked(mfg_item, batch)
    location = WarehouseLocationFactory.it(is_putaway=True)
    inbound = InboundWarehouseOrderFactory.it(
        order=None,
        manufacturing_order=mfg_item.order,
        state=InboundWarehouseOrderState.IN_TRANSIT,
        pickup_location=location,
    )
    warehouse_service.confirm_arrival(inbound.code, location.code, context=context)

    from apps.warehouse.models.warehouse import WarehouseItem

    warehouse_service.confirm_draft(inbound.code, context=context)

    produced = WarehouseItem.objects.get(order_in=inbound)
    assert produced.batch == batch
