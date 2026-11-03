from datetime import datetime, timezone as dt_timezone
from unittest import mock

import pytest

from apps.warehouse.core.services.code_sequence import generate_next_sequential_code
from apps.warehouse.core.services.manufacturing import ManufacturingOrdersService
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.services.outbound_calculations import (
    outbound_calculations_service,
)
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.core.services.warehouse_order_factory import generate_next_code
from apps.warehouse.models.orders import InboundOrder
from apps.warehouse.models.settings import CodeSequence, GlobalSettings
from apps.warehouse.models.warehouse import InboundWarehouseOrder
from apps.warehouse.tests.factories.manufacturing import ManufacturingOrderFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    OutboundCalculationFactory,
    OutboundOrderFactory,
)
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory
from apps.warehouse.tests.factories.warehouse import InboundWarehouseOrderFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=dt_timezone.utc)


@pytest.fixture(autouse=True)
def frozen_now():
    with mock.patch(
        "apps.warehouse.core.services.code_sequence.timezone.now", return_value=NOW
    ):
        yield


def _use(sequence: CodeSequence) -> None:
    GlobalSettingsFactory()  # make sure the singleton exists
    GlobalSettings.objects.filter(pk=1).update(code_sequence=sequence)


def _next_inbound() -> str:
    return generate_next_sequential_code(
        queryset=InboundOrder.objects.all(), prefix="OV"
    )


def test_default_setting_is_yearly() -> None:
    assert GlobalSettings.load().code_sequence == CodeSequence.YEARLY


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        (CodeSequence.YEARLY, "OV202600001"),
        (CodeSequence.MONTHLY, "OV2026110001"),
    ],
)
def test_first_code_of_period(sequence, expected) -> None:
    _use(sequence)
    assert _next_inbound() == expected


@pytest.mark.parametrize(
    ("sequence", "existing", "expected"),
    [
        # continues after the highest code, gaps are not filled
        (CodeSequence.YEARLY, ["OV202600001", "OV202600007"], "OV202600008"),
        (CodeSequence.MONTHLY, ["OV2026110001", "OV2026110007"], "OV2026110008"),
        # yearly sequence spans months, the monthly one restarts each month
        (CodeSequence.YEARLY, ["OV202600041"], "OV202600042"),
        (CodeSequence.MONTHLY, ["OV2026100041"], "OV2026110001"),
        # previous year never counts
        (CodeSequence.YEARLY, ["OV202500099"], "OV202600001"),
        # codes of the other layout and foreign codes are ignored
        (CodeSequence.YEARLY, ["OV2026110005", "ORD-0001"], "OV202600001"),
        (CodeSequence.MONTHLY, ["OV202600005", "ORD-0001"], "OV2026110001"),
    ],
)
def test_next_code_continues_the_sequence(sequence, existing, expected) -> None:
    _use(sequence)
    for code in existing:
        InboundOrderFactory(code=code)
    assert _next_inbound() == expected


def test_switching_setting_changes_the_layout_of_new_codes() -> None:
    _use(CodeSequence.MONTHLY)
    InboundOrderFactory(code=_next_inbound())
    _use(CodeSequence.YEARLY)
    assert _next_inbound() == "OV202600001"


@pytest.mark.parametrize(
    ("generate", "prefix"),
    [
        (inbound_orders_service.generate_next_incoming_order_code, "OV"),
        (outbound_orders_service.generate_next_outgoing_order_code, "OP"),
        (outbound_calculations_service.generate_next_calculation_code, "K"),
        (ManufacturingOrdersService.generate_next_code, "PV"),
    ],
)
@pytest.mark.parametrize(
    ("sequence", "suffix"),
    [(CodeSequence.YEARLY, "202600001"), (CodeSequence.MONTHLY, "2026110001")],
)
def test_all_document_generators_honour_the_setting(
    generate, prefix, sequence, suffix
) -> None:
    _use(sequence)
    assert generate() == f"{prefix}{suffix}"


def test_generators_continue_existing_yearly_codes() -> None:
    _use(CodeSequence.YEARLY)
    OutboundOrderFactory(code="OP202600003")
    OutboundCalculationFactory(code="K202600003")
    ManufacturingOrderFactory(code="PV202600003")

    assert outbound_orders_service.generate_next_outgoing_order_code() == "OP202600004"
    assert (
        outbound_calculations_service.generate_next_calculation_code() == "K202600004"
    )
    assert ManufacturingOrdersService.generate_next_code() == "PV202600004"


def test_warehouse_order_without_parent_uses_the_setting() -> None:
    _use(CodeSequence.YEARLY)
    InboundWarehouseOrderFactory(code="P202600002")

    assert generate_next_code(InboundWarehouseOrder, "P") == "P202600003"
