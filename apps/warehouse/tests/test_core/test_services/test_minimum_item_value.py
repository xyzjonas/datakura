from decimal import Decimal

import pytest

from apps.warehouse.core.services.settings import (
    MinimumItemValueSource,
    settings_service,
)
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory


@pytest.mark.parametrize(
    "global_min, enabled, override, expected",
    [
        # nothing configured
        (0, True, None, None),
        # global applies
        (5, True, None, (5, MinimumItemValueSource.GLOBAL)),
        # customer override beats global (both lower and higher)
        (5, True, 2, (2, MinimumItemValueSource.CUSTOMER)),
        (5, True, 50, (50, MinimumItemValueSource.CUSTOMER)),
        # override works without a global minimum
        (0, True, 7, (7, MinimumItemValueSource.CUSTOMER)),
        # override of 0 means "no minimum" for this customer, not "use global"
        (5, True, 0, None),
        # turned off completely, regardless of anything else
        (5, False, None, None),
        (5, False, 50, None),
    ],
)
def test_resolve_minimum_item_value(db, global_min, enabled, override, expected):
    GlobalSettingsFactory(minimum_item_value=global_min)
    customer = CustomerFactory(
        minimum_item_value_enabled=enabled, minimum_item_value=override
    )

    result = settings_service.resolve_minimum_item_value(customer)

    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert result.value == Decimal(expected[0])
        assert result.source == expected[1]


def test_resolve_minimum_item_value_without_customer_uses_global(db):
    GlobalSettingsFactory(minimum_item_value=5)

    result = settings_service.resolve_minimum_item_value(None)

    assert result is not None and result.value == 5


@pytest.mark.parametrize(
    "total, expected",
    [
        ("0", "5"),
        ("0.10", "5"),
        ("4.9999", "5"),
        # interval boundaries: exactly the minimum and just above stay untouched
        ("5", "5"),
        ("5.0001", "5.0001"),
        ("100", "100"),
    ],
)
def test_apply_minimum_item_value(db, total, expected):
    GlobalSettingsFactory(minimum_item_value=5)
    customer = CustomerFactory()

    result = settings_service.apply_minimum_item_value(customer, Decimal(total))

    assert result == Decimal(expected)


def test_apply_minimum_item_value_keeps_total_when_disabled(db):
    GlobalSettingsFactory(minimum_item_value=5)
    customer = CustomerFactory(minimum_item_value_enabled=False)

    assert settings_service.apply_minimum_item_value(
        customer, Decimal("0.10")
    ) == Decimal("0.10")
