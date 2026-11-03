import pytest

from apps.warehouse.models.orders import InboundOrder, OutboundOrder

from apps.warehouse.core.services.warehouse_order_factory import (
    WarehouseOrderKind,
    create_warehouse_order,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    OutboundOrderFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
)

pytestmark = pytest.mark.django_db


def _inbound(code: str) -> InboundOrder:
    return InboundOrderFactory(code=code)  # type: ignore[return-value]


def _outbound(code: str) -> OutboundOrder:
    return OutboundOrderFactory(code=code)  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("order_code", "expected_prefix_part"),
    [
        ("OP2026110003", "2026110003"),
        ("OV2026110010", "2026110010"),
        ("ORD-0042", "0042"),
    ],
)
def test_inbound_code_uses_numeric_part_of_order_code(
    context, order_code, expected_prefix_part
) -> None:
    order = _inbound(order_code)
    wo = create_warehouse_order(
        WarehouseOrderKind.INBOUND, context, purchase_order=order
    )
    assert wo.code == f"P{expected_prefix_part}001"


def test_sales_outbound_code_uses_numeric_part_of_order_code(context) -> None:
    order = _outbound("OP2026110003")
    wo = create_warehouse_order(
        WarehouseOrderKind.SALES_OUTBOUND, context, sales_order=order
    )
    assert wo.code == "WO2026110003001"


def test_inbound_suffix_increments_across_children(context) -> None:
    order = _inbound("OV2026110003")
    primary = create_warehouse_order(
        WarehouseOrderKind.INBOUND, context, purchase_order=order
    )
    child1 = create_warehouse_order(
        WarehouseOrderKind.CHILD_INBOUND, context, primary_order=primary
    )
    child2 = create_warehouse_order(
        WarehouseOrderKind.CHILD_INBOUND, context, primary_order=primary
    )
    assert [primary.code, child1.code, child2.code] == [
        "P2026110003001",
        "P2026110003002",
        "P2026110003003",
    ]


def test_outbound_suffix_increments_across_children(context) -> None:
    order = _outbound("OP2026110003")
    primary = create_warehouse_order(
        WarehouseOrderKind.SALES_OUTBOUND, context, sales_order=order
    )
    child = create_warehouse_order(
        WarehouseOrderKind.CHILD_OUTBOUND, context, primary_order=primary
    )
    assert child.code == "V2026110003002"


def test_suffix_is_independent_per_order(context) -> None:
    a = _inbound("OV2026110001")
    b = _inbound("OV2026110002")
    create_warehouse_order(WarehouseOrderKind.INBOUND, context, purchase_order=a)
    wo_b = create_warehouse_order(WarehouseOrderKind.INBOUND, context, purchase_order=b)
    assert wo_b.code == "P2026110002001"


def test_legacy_codes_do_not_break_sequence(context) -> None:
    order = _inbound("OV2026110003")
    InboundWarehouseOrderFactory(code="P2026110001", order=order)  # legacy format
    wo = create_warehouse_order(
        WarehouseOrderKind.INBOUND, context, purchase_order=order
    )
    assert wo.code == "P2026110003001"
