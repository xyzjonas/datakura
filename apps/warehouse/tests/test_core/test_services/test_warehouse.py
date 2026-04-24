from decimal import Decimal

import pytest
from django.utils import timezone

from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    ApiBaseException,
    ErrorCode,
)
from apps.warehouse.core.schemas.warehouse import (
    WarehouseOrderCreateSchema,
    WarehouseItemSchema,
    DraftItemAddSchema,
)
from apps.warehouse.core.services.warehouse import (
    warehouse_service,
    get_or_create_batch,
)
from apps.warehouse.core.transformation import (
    product_orm_to_schema,
    location_orm_to_schema,
    package_orm_to_schema,
)
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.orders import (
    CreditNoteState,
    InboundOrderState,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import (
    WarehouseLocation,
    WarehouseItem,
    InboundWarehouseOrderItem,
    WarehouseMovement,
    Batch,
    InboundWarehouseOrderState,
    TrackingLevel,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.units import UnitOfMeasureFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseLocationFactory,
)


def test_create_warehouse_inbound_order(context):
    putaway = WarehouseLocationFactory.it(is_putaway=True)
    order = InboundOrderFactory()
    InboundOrderItemFactory.create_batch(10, order=order)

    result = warehouse_service.create_inbound_order(
        WarehouseOrderCreateSchema(purchase_order_code=order.code),
        context=context,
    )

    assert len(result.items) == 0
    assert result.state == InboundWarehouseOrderState.get_label(
        InboundWarehouseOrderState.IN_TRANSIT
    )

    warehouse_service.confirm_arrival(result.code, putaway.code, context=context)
    result = warehouse_service.get_inbound_warehouse_order(result.code)

    assert result.state == InboundWarehouseOrderState.get_label(
        InboundWarehouseOrderState.DRAFT
    )
    assert len(result.order_items) == 10
    assert len(result.items) == 0  # WarehouseItems not yet materialised in DRAFT


def test_confirm_arrival_requires_in_transit_state(db, context):
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.DRAFT)
    location = WarehouseLocationFactory()

    with pytest.raises(WarehouseGenericError):
        warehouse_service.confirm_arrival(order.code, location.code, context=context)


@pytest.mark.parametrize("items_amount, amount", [(3, 99), (0, 10), (3, 1.2)])
def test_get_warehouse_availability(db, items_amount, amount):
    product = StockProductFactory.it()
    WarehouseItemFactory.create_batch(
        items_amount,
        amount=amount,
        stock_product=product,
        order_in=InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING),
    )
    assert warehouse_service.get_warehouse_availability(product.code) == pytest.approx(
        Decimal(items_amount * amount)
    )


@pytest.mark.parametrize("items_amount, amount", [(10, 10), (0, 10), (3, 1.2)])
def test_get_total_availability(db, items_amount, amount):
    product = StockProductFactory.it()
    WarehouseItemFactory.create_batch(
        items_amount,
        amount=amount,
        stock_product=product,
        order_in=InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING),
    )
    result = warehouse_service.get_total_availability(product.code)
    assert result.total_amount == pytest.approx(Decimal(items_amount * amount))
    assert result.available_amount == pytest.approx(Decimal(items_amount * amount))
    assert result.incoming_amount == pytest.approx(Decimal(0))


@pytest.mark.parametrize("items_amount, amount", [(3, 99), (0, 10), (3, 1.2)])
def test_get_incoming_availability(db, items_amount, amount):
    """Test calculation of incoming items from draft inbound orders"""
    product = StockProductFactory.it()
    order = InboundOrderFactory(state=InboundOrderState.DRAFT)
    InboundOrderItemFactory.create_batch(
        items_amount,
        amount=amount,
        stock_product=product,
        order=order,
    )
    assert warehouse_service.get_incoming_availability(product.code) == pytest.approx(
        Decimal(items_amount * amount)
    )


@pytest.mark.parametrize("items_amount, amount", [(3, 99), (0, 10), (5, 2.5)])
def test_get_incoming_availability_in_transit(db, items_amount, amount):
    """Test that submitted inbound order items are counted as incoming"""
    product = StockProductFactory.it()
    order = InboundOrderFactory(state=InboundOrderState.SUBMITTED)
    InboundOrderItemFactory.create_batch(
        items_amount,
        amount=amount,
        stock_product=product,
        order=order,
    )
    assert warehouse_service.get_incoming_availability(product.code) == pytest.approx(
        Decimal(items_amount * amount)
    )


def test_get_incoming_availability_excludes_available_items(db):
    """Test that incoming doesn't count items from completed/pending inbound orders"""
    product = StockProductFactory.it()
    # Create incoming items
    InboundOrderItemFactory.create_batch(
        2,
        amount=10,
        stock_product=product,
        order=InboundOrderFactory(state=InboundOrderState.DRAFT),
    )
    # Create items that are already available
    InboundOrderItemFactory.create_batch(
        3,
        amount=10,
        stock_product=product,
        order=InboundOrderFactory(state=InboundOrderState.PUTAWAY),
    )
    # Incoming should only count the DRAFT items
    assert warehouse_service.get_incoming_availability(product.code) == pytest.approx(
        Decimal(20)
    )


@pytest.mark.parametrize("amount", [(10), (5.5), (0)])
def test_get_booked_availability(db, amount):
    """Test calculation of booked items from submitted outbound orders"""
    product = StockProductFactory.it()
    outbound_order = OutboundOrderFactory(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(amount),
        order=outbound_order,
    )

    booked = warehouse_service.get_booked_availability(product.code)
    assert booked == pytest.approx(Decimal(amount))


def test_get_booked_availability_started(db):
    """Test that picking outbound orders are included in booked calculation"""
    product = StockProductFactory.it()
    outbound_order = OutboundOrderFactory(state=OutboundOrderState.PICKING)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(15),
        order=outbound_order,
    )

    booked = warehouse_service.get_booked_availability(product.code)
    assert booked == pytest.approx(Decimal(15))


def test_get_booked_availability_excludes_completed(db):
    """Test that completed outbound orders are not counted as booked"""
    product = StockProductFactory.it()

    # Create completed outbound order
    completed_order = OutboundOrderFactory(state=OutboundOrderState.COMPLETED)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(10),
        order=completed_order,
    )

    # Create pending outbound order
    pending_order = OutboundOrderFactory(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(5),
        order=pending_order,
    )

    booked = warehouse_service.get_booked_availability(product.code)
    # Should only count the pending order
    assert booked == pytest.approx(Decimal(5))


def test_get_booked_availability_excludes_completed_paid(db):
    product = StockProductFactory.it()
    paid_order = OutboundOrderFactory(state=OutboundOrderState.COMPLETED_PAID)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(8),
        order=paid_order,
    )

    active_order = OutboundOrderFactory(state=OutboundOrderState.PICKING)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(3),
        order=active_order,
    )

    booked = warehouse_service.get_booked_availability(product.code)
    assert booked == pytest.approx(Decimal(3))


def test_get_total_availability_with_incoming_and_booked(db):
    """Test total availability with incoming items and booked items"""
    product = StockProductFactory.it()

    # Create available stock
    WarehouseItemFactory.create_batch(
        5,
        amount=10,
        stock_product=product,
        order_in=InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING),
    )  # 50 items available

    # Create incoming stock
    InboundOrderItemFactory.create_batch(
        2,
        amount=10,
        stock_product=product,
        order=InboundOrderFactory(state=InboundOrderState.DRAFT),
    )  # 20 items incoming

    # Create booked stock
    outbound_order = OutboundOrderFactory(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory.create(
        stock_product=product,
        amount=Decimal(15),
        order=outbound_order,
    )  # 15 items booked

    result = warehouse_service.get_total_availability(product.code)
    assert result.total_amount == pytest.approx(Decimal(50))  # stocked amount only
    assert result.available_amount == pytest.approx(
        Decimal(35)
    )  # 50 - 15 available - booked
    assert result.incoming_amount == pytest.approx(Decimal(20))  # 20 incoming


def test_get_warehouse_availability_includes_pending_inbound_items_in_putaway(db):
    product = StockProductFactory.it()
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    inbound_order = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )

    WarehouseItemFactory(
        stock_product=product,
        amount=Decimal("12"),
        order_in=inbound_order,
        location=putaway_location,
    )

    assert warehouse_service.get_warehouse_availability(product.code) == pytest.approx(
        Decimal("12")
    )


def test_update_inbound_order_items(db, context):
    order = InboundWarehouseOrderFactory()
    product = StockProductFactory()
    old_item = InboundWarehouseOrderItemFactory(warehouse_order=order, amount=10)

    count = 3
    new_items = [
        DraftItemAddSchema(product_code=product.code, amount=5) for _ in range(count)
    ]

    result = warehouse_service.add_or_remove_inbound_order_items(
        order.code, [old_item.pk], new_items, context=context
    )
    assert not InboundWarehouseOrderItem.objects.filter(pk=old_item.pk).exists()
    assert result.code == order.code
    assert result.state == InboundWarehouseOrderState.get_label(order.state)
    assert len(result.order_items) == count
    for item in result.order_items:
        assert item.amount == Decimal("5")
        assert item.product.code == product.code


def test_setup_tracking_for_inbound_order_item_total(db, context):
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    product = StockProductFactory()
    order_item = InboundWarehouseOrderItemFactory(
        warehouse_order=order, stock_product=product, amount=10
    )

    count = 10
    new_items = [
        WarehouseItemSchema(
            id=-1,
            unit_of_measure=product.unit_of_measure.name,
            created=timezone.now(),
            changed=timezone.now(),
            product=product_orm_to_schema(product),
            location=location_orm_to_schema(WarehouseLocationFactory()),
            amount=1,
            package=package_orm_to_schema(pkg),
            tracking_level=TrackingLevel.FUNGIBLE,
        )
        for _ in range(count)
    ]

    result = warehouse_service.setup_tracking_for_inbound_order_item(
        order.code, order_item.pk, new_items, context=context
    )
    assert not InboundWarehouseOrderItem.objects.filter(pk=order_item.pk).exists()
    assert result.code == order.code
    assert result.state == InboundWarehouseOrderState.get_label(order.state)
    assert len(result.order_items) == count
    for item in result.order_items:
        assert item.package is not None
        assert item.package.type == pkg.name
        assert item.product.code == product.code


def test_setup_tracking_for_inbound_order_item_remaining(db, context):
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    product = StockProductFactory()
    order_item = InboundWarehouseOrderItemFactory(
        warehouse_order=order, stock_product=product, amount=20
    )

    count = 10
    new_items = [
        WarehouseItemSchema(
            id=-1,
            unit_of_measure=product.unit_of_measure.name,
            created=timezone.now(),
            changed=timezone.now(),
            product=product_orm_to_schema(product),
            location=location_orm_to_schema(WarehouseLocationFactory()),
            amount=1,
            package=package_orm_to_schema(pkg),
            tracking_level=TrackingLevel.FUNGIBLE,
        )
        for _ in range(count)
    ]

    result = warehouse_service.setup_tracking_for_inbound_order_item(
        order.code, order_item.pk, new_items, context=context
    )

    # Original item still exists with reduced amount
    order_item.refresh_from_db()
    assert order_item.amount == 10

    assert result.code == order.code
    packaged = [item for item in result.order_items if item.package is not None]
    unpackaged = [item for item in result.order_items if item.package is None]
    assert len(packaged) == count
    assert len(unpackaged) == 1
    for item in unpackaged:
        assert item.product.code == product.code


def test_get_or_create_batch_creates_new_batch_with_primary_barcode(db):
    batch_barcode = "05BM0000983"

    batch, created = get_or_create_batch(batch_barcode)

    assert created is True
    barcode = Barcode.objects.get(code=batch_barcode)
    assert barcode.content_object == batch
    assert barcode.is_primary is True


def test_get_or_create_batch_returns_existing_batch_by_barcode(db):
    batch_barcode = "05BM0000983"
    existing_batch = Batch.objects.create()
    existing_batch.attach_barcode(batch_barcode, is_primary=True)

    batch, created = get_or_create_batch(batch_barcode)

    assert created is False
    assert batch.pk == existing_batch.pk


def test_preview_serial_tracking_creates_one_item_per_amount(db):
    pickup_location = WarehouseLocationFactory()
    w_order = InboundWarehouseOrderFactory(pickup_location=pickup_location)
    order_item = InboundWarehouseOrderItemFactory(warehouse_order=w_order, amount=10)

    result = warehouse_service.preview_serial_tracking(
        order_item_id=order_item.pk,
        product_code=order_item.stock_product.code,
        amount=3,
    )

    assert len(result) == 3
    for item in result:
        assert item.tracking_level == TrackingLevel.SERIALIZED_PIECE
        assert item.amount == 1.0
        assert item.package is None
        assert item.batch is None
        assert item.location.code == pickup_location.code
        assert item.product.code == order_item.stock_product.code
        assert item.primary_barcode is not None
        assert len(item.primary_barcode) == 13


@pytest.mark.parametrize("amount", [0, -1, 1.5])
def test_preview_serial_tracking_requires_positive_whole_amount(db, amount):
    pickup_location = WarehouseLocationFactory()
    w_order = InboundWarehouseOrderFactory(pickup_location=pickup_location)
    order_item = InboundWarehouseOrderItemFactory(warehouse_order=w_order)

    with pytest.raises(ApiBaseException) as exc:
        warehouse_service.preview_serial_tracking(
            order_item_id=order_item.pk,
            product_code=order_item.stock_product.code,
            amount=amount,
        )

    assert exc.value.code == ErrorCode.INVALID_CONVERSION


def test_dissolve_inbound_order_item_create(db):
    """Dissolve a tracked draft item — a new FUNGIBLE item is created."""
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    product = StockProductFactory()
    packaged_item = InboundWarehouseOrderItemFactory(
        warehouse_order=order,
        stock_product=product,
        amount=10,
        package_type=pkg,
        tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
    )

    warehouse_service.dissolve_inbound_order_item(order.code, packaged_item.pk)

    order_items = list(order.order_items.all())
    assert len(order_items) == 1
    item = order_items[0]
    assert item.amount == 10
    assert item.package_type is None
    assert item.tracking_level == TrackingLevel.FUNGIBLE

    assert not InboundWarehouseOrderItem.objects.filter(pk=packaged_item.pk).exists()


def test_dissolve_inbound_order_item_add(db):
    """Dissolve tracked item — amount merges into existing FUNGIBLE item."""
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    product = StockProductFactory()
    # Unrelated item (different product, should be untouched)
    InboundWarehouseOrderItemFactory(warehouse_order=order, amount=99)
    fungible_item = InboundWarehouseOrderItemFactory(
        warehouse_order=order,
        stock_product=product,
        amount=10,
        tracking_level=TrackingLevel.FUNGIBLE,
    )
    packaged_item = InboundWarehouseOrderItemFactory(
        warehouse_order=order,
        stock_product=product,
        amount=10,
        package_type=pkg,
        tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
    )

    warehouse_service.dissolve_inbound_order_item(order.code, packaged_item.pk)

    fungible_item.refresh_from_db()
    assert fungible_item.amount == 20
    assert not InboundWarehouseOrderItem.objects.filter(pk=packaged_item.pk).exists()


def test_remove_from_order_to_credit_note(db, context):
    amount = 100
    unit_price = 99
    w_order = InboundWarehouseOrderFactory.create_complete(
        amount=amount, unit_price=unit_price
    )
    # credit note operates on InboundWarehouseOrderItem in DRAFT state
    order_item = w_order.order_items.first()
    assert order_item is not None

    credited_amount = 10
    result = warehouse_service.remove_from_order_to_credit_note(
        w_order.code, order_item.pk, credited_amount, context=context
    )
    credit_note = result.credit_note
    assert credit_note
    assert credit_note.state == CreditNoteState.get_label(CreditNoteState.DRAFT)
    assert credit_note.order.code == result.order.code
    assert len(credit_note.items) == 1

    credit_item = credit_note.items[0]
    assert credit_item.product.code == order_item.stock_product.code
    assert credit_item.amount == credited_amount
    assert credit_item.unit_price == unit_price

    order_item.refresh_from_db()
    assert order_item.amount == amount - credited_amount


def test_remove_from_order_to_credit_note_all_gone(db, context):
    amount = 100
    w_order = InboundWarehouseOrderFactory.create_complete(amount=amount, unit_price=1)
    order_item = w_order.order_items.first()
    assert order_item is not None

    credited_amount = amount
    result = warehouse_service.remove_from_order_to_credit_note(
        w_order.code, order_item.pk, credited_amount, context=context
    )
    assert len(result.credit_note.items) == 1

    credit_item = result.credit_note.items[0]
    assert credit_item.product.code == order_item.stock_product.code
    assert credit_item.amount == credited_amount

    assert not InboundWarehouseOrderItem.objects.filter(pk=order_item.pk).exists()


def test_putaway_item_simple(db, context):
    new_location = WarehouseLocationFactory()
    war_order = InboundWarehouseOrderFactory.create_complete(
        amount=10, state=InboundWarehouseOrderState.PENDING
    )

    warehouse_service.putaway_item(
        war_order.items.first().pk, war_order.code, new_location.code, context=context
    )

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == 10
    assert item.location.code == new_location.code
    assert item.package_type is None


def test_putaway_item_packaged(db, context):
    piece_uom = UnitOfMeasureFactory(name="KS")
    box_100 = PackageTypeFactory(name="B0100", unit_of_measure=piece_uom)
    stock_product = StockProductFactory(unit_of_measure=piece_uom)
    new_location = WarehouseLocationFactory()

    war_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    packaged = WarehouseItemFactory(
        stock_product=stock_product,
        order_in=war_order,
        amount=100,
        package_type=box_100,
    )
    InboundOrderItemFactory(order=war_order.order, stock_product=stock_product)

    warehouse_service.putaway_item(
        packaged.pk, war_order.code, new_location.code, context=context
    )

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == 100
    assert item.package_type == box_100


def test_putaway_item_unpackaged_merge(db, context):
    piece_uom = UnitOfMeasureFactory(name="KS")
    stock_product = StockProductFactory(unit_of_measure=piece_uom)
    new_location = WarehouseLocationFactory()

    # new location already has the same untracked stock-product-item, it has to be merged
    WarehouseItemFactory(stock_product=stock_product, amount=50, location=new_location)

    war_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    InboundOrderItemFactory(order=war_order.order, stock_product=stock_product)
    unpackaged = WarehouseItemFactory(
        stock_product=stock_product, order_in=war_order, amount=10
    )
    old_pk = unpackaged.pk

    warehouse_service.putaway_item(
        unpackaged.pk, war_order.code, new_location.code, context=context
    )

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == Decimal(str(50 + 10))
    assert item.package_type is None

    with pytest.raises(WarehouseItem.DoesNotExist):
        assert WarehouseItem.objects.get(pk=old_pk)


@pytest.mark.parametrize(
    "state",
    [
        InboundWarehouseOrderState.DRAFT,
        InboundWarehouseOrderState.COMPLETED,
        InboundWarehouseOrderState.CANCELLED,
    ],
)
def test_putaway_item_invalid_order_state(db, state, context):
    new_location = WarehouseLocationFactory()
    war_order = InboundWarehouseOrderFactory(state=state)
    unpackaged = WarehouseItemFactory(order_in=war_order)

    with pytest.raises(WarehouseGenericError):
        warehouse_service.putaway_item(
            unpackaged.pk, war_order.code, new_location.code, context=context
        )


def test_start_inbound_order(db, context):
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    to_be_moved = WarehouseItemFactory(order_in=order, location=putaway_location)
    InboundOrderItemFactory(order=order.order, stock_product=to_be_moved.stock_product)
    WarehouseItemFactory.create_batch(9, order_in=order, location=putaway_location)

    new_location = WarehouseLocationFactory(is_putaway=False)

    warehouse_service.putaway_item(
        to_be_moved.pk, order.code, new_location.code, context=context
    )

    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.STARTED
    assert order.items.filter(location__is_putaway=True).count() == 9


def test_complete_inbound_order(db, context):
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.PENDING)
    to_be_moved_1 = WarehouseItemFactory.it(order_in=order, location=putaway_location)
    to_be_moved_2 = WarehouseItemFactory.it(order_in=order, location=putaway_location)

    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_1.stock_product
    )
    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_2.stock_product
    )

    new_location = WarehouseLocationFactory(is_putaway=False)

    warehouse_service.putaway_item(
        item_id=to_be_moved_1.pk,
        warehouse_order_code=order.code,
        new_location_code=new_location.code,
        context=context,
    )
    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.STARTED

    warehouse_service.putaway_item(
        item_id=to_be_moved_2.pk,
        warehouse_order_code=order.code,
        new_location_code=new_location.code,
        context=context,
    )
    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.COMPLETED


def test_complete_inbound_order_only_after_last_child_order_closed(db, context):
    """
    Scenario:
    1 inbound order -> 1st warehouse order -> offload to 2nd -> offload to 3rd.

    Base inbound order must be marked COMPLETED only after the last warehouse
    order in the chain is completed.
    """
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    final_location = WarehouseLocationFactory(is_putaway=False)

    inbound_order = InboundOrderFactory(state=InboundOrderState.PUTAWAY)
    first_order = InboundWarehouseOrderFactory(
        order=inbound_order,
        state=InboundWarehouseOrderState.PENDING,
    )

    item_in_first = WarehouseItemFactory(
        order_in=first_order,
        location=putaway_location,
        amount=Decimal("4"),
    )
    InboundOrderItemFactory(
        order=inbound_order,
        stock_product=item_in_first.stock_product,
        amount=Decimal("4"),
        unit_price=Decimal("10"),
    )

    # 1st -> 2nd (move part of item, keep some in 1st)
    warehouse_service.offload_items_to_child_order(
        parent_code=first_order.code,
        items=[(item_in_first.pk, Decimal("2"))],
        context=context,
    )
    second_order = first_order.derived_orders.get()
    item_in_second = second_order.items.get()

    # 2nd -> 3rd (move part of item, keep some in 2nd)
    warehouse_service.offload_items_to_child_order(
        parent_code=second_order.code,
        items=[(item_in_second.pk, Decimal("1"))],
        context=context,
    )
    third_order = second_order.derived_orders.get()

    # Child orders must be confirmed before putaway can happen.
    warehouse_service.transition_order(
        second_order.code, InboundWarehouseOrderState.PENDING, context=context
    )
    warehouse_service.transition_order(
        third_order.code, InboundWarehouseOrderState.PENDING, context=context
    )

    # Complete 1st order -> base inbound order must stay open.
    item_in_first.refresh_from_db()
    warehouse_service.putaway_item(
        item_id=item_in_first.pk,
        warehouse_order_code=first_order.code,
        new_location_code=final_location.code,
        context=context,
    )
    inbound_order.refresh_from_db()
    first_order.refresh_from_db()
    assert first_order.state == InboundWarehouseOrderState.COMPLETED
    assert inbound_order.state != InboundOrderState.COMPLETED

    # Complete 2nd order -> base inbound order must still stay open.
    item_in_second.refresh_from_db()
    warehouse_service.putaway_item(
        item_id=item_in_second.pk,
        warehouse_order_code=second_order.code,
        new_location_code=final_location.code,
        context=context,
    )
    inbound_order.refresh_from_db()
    second_order.refresh_from_db()
    assert second_order.state == InboundWarehouseOrderState.COMPLETED
    assert inbound_order.state != InboundOrderState.COMPLETED

    # Complete 3rd (last) order -> now base inbound order must be completed.
    item_in_third = third_order.items.get()
    warehouse_service.putaway_item(
        item_id=item_in_third.pk,
        warehouse_order_code=third_order.code,
        new_location_code=final_location.code,
        context=context,
    )
    inbound_order.refresh_from_db()
    third_order.refresh_from_db()
    assert third_order.state == InboundWarehouseOrderState.COMPLETED
    assert inbound_order.state == InboundOrderState.COMPLETED


@pytest.mark.parametrize(
    "amount_pre, price_pre, amount_in, price_in, expected",
    [
        (0, 1000, 1, 1, 1),
        (1, 1, 1, 1, 1),
        (1, 1, 1, 2, 1.5),
        (10, 10, 5, 20, 13.33),
        (0, 0, 10, 5, 5),
        (5, 10, 0, 0, 10),
        (100, 1.5, 200, 2.0, 1.83),
        (7, 3.2, 15, 4.1, 3.81),
        (120, 0.5, 30, 0.7, 0.54),
    ],
)
def test_recalculate_average_purchase_price_existing_stock(
    db, price_in, price_pre, amount_pre, amount_in, expected, context
):
    product = StockProductFactory.it(purchase_price=price_pre)
    WarehouseItemFactory(
        stock_product=product,
        amount=amount_pre,
        order_in=InboundWarehouseOrderFactory(
            state=InboundWarehouseOrderState.COMPLETED
        ),
    )
    w_order = InboundWarehouseOrderFactory.create_complete(
        product=product,
        amount=amount_in,
        unit_price=price_in,
        is_putaway=True,
        state=InboundWarehouseOrderState.PENDING,
    )

    assert WarehouseItem.objects.filter(order_in=w_order).count() == 1
    item = WarehouseItem.objects.filter(order_in=w_order).first()

    warehouse_service.recalculate_average_purchase_price(
        product.code, item.amount, price_in, context=context
    )

    product.refresh_from_db()
    assert product.purchase_price == pytest.approx(Decimal(expected))


def test_create_warehouse_movement_fungible_sets_item_and_batch_none(db):
    order = InboundWarehouseOrderFactory()
    source_location = WarehouseLocationFactory()
    target_location = WarehouseLocationFactory()
    item = WarehouseItemFactory(
        order_in=order,
        location=source_location,
        tracking_level=TrackingLevel.FUNGIBLE,
    )

    warehouse_service.create_warehouse_movement(
        item.pk, order.code, target_location.code
    )

    movement = WarehouseMovement.objects.filter(item__isnull=True).latest("id")
    assert movement.location_from == source_location
    assert movement.location_to == target_location
    assert movement.inbound_order_code == order
    assert movement.stock_product == item.stock_product
    assert movement.amount == item.amount
    assert movement.item is None
    assert movement.batch is None


def test_create_warehouse_movement_batch_sets_batch_only(db):
    order = InboundWarehouseOrderFactory()
    source_location = WarehouseLocationFactory()
    target_location = WarehouseLocationFactory()
    batch = Batch.objects.create(description="b-1")
    item = WarehouseItemFactory(
        order_in=order,
        location=source_location,
        tracking_level=TrackingLevel.BATCH,
        batch=batch,
    )

    warehouse_service.create_warehouse_movement(
        item.pk, order.code, target_location.code
    )

    movement = WarehouseMovement.objects.filter(inbound_order_code=order).latest("id")
    assert movement.location_from == source_location
    assert movement.location_to == target_location
    assert movement.stock_product == item.stock_product
    assert movement.amount == item.amount
    assert movement.item is None
    assert movement.batch == batch


@pytest.mark.parametrize(
    "tracking_level", [TrackingLevel.SERIALIZED_PIECE, TrackingLevel.SERIALIZED_PACKAGE]
)
def test_create_warehouse_movement_serialized_sets_item_only(db, tracking_level):
    order = InboundWarehouseOrderFactory()
    source_location = WarehouseLocationFactory()
    target_location = WarehouseLocationFactory()
    item = WarehouseItemFactory(
        order_in=order,
        location=source_location,
        tracking_level=tracking_level,
    )

    warehouse_service.create_warehouse_movement(
        item.pk, order.code, target_location.code
    )

    movement = WarehouseMovement.objects.filter(inbound_order_code=order).latest("id")
    assert movement.location_from == source_location
    assert movement.location_to == target_location
    assert movement.stock_product == item.stock_product
    assert movement.amount == item.amount
    assert movement.item == item
    assert movement.batch is None
