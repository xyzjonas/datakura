import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.stock_import import (
    IMPORT_TRACKING_LEVEL,
    StockImportService,
)
from apps.warehouse.models.warehouse import Warehouse, WarehouseItem, WarehouseLocation
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseFactory,
    WarehouseLocationFactory,
)


def _place(code: str, *items: tuple[str, object], name: str | None = None) -> dict:
    return {
        "Id": 1,
        "Code": code,
        "Name": name or code,
        "StockItems": [
            {"Id": i, "StockProductCode": c, "Value": v, "Price": 123.456, "Note": None}
            for i, (c, v) in enumerate(items)
        ],
    }


def _payload(*places: dict) -> str:
    return json.dumps(
        {"Id": 1, "Code": "C", "Name": "Centrála", "WarehousePlaces": list(places)}
    )


@pytest.fixture
def products(db):
    return {c: StockProductFactory(code=c) for c in ("P-1", "P-2")}


@pytest.mark.django_db
def test_import_blank_database(products):
    raw = _payload(
        _place("AA-01-00", ("P-1", 0.33), ("P-2", 10.55), name="﻿AA-01-00"),
        _place("AA-01-01", ("P-1", "5.10")),
    )

    summary = StockImportService("Main").import_from_json(raw)

    assert summary.warehouse_created
    assert (summary.locations_created, summary.items_created) == (2, 3)
    warehouse = Warehouse.objects.get(name="Main")
    assert set(warehouse.locations.values_list("code", flat=True)) == {
        "AA-01-00",
        "AA-01-01",
    }
    item = WarehouseItem.objects.get(
        location__code="AA-01-00", stock_product__code="P-2"
    )
    assert item.amount == Decimal("10.55")
    assert item.tracking_level == IMPORT_TRACKING_LEVEL
    assert item.order_in is None


@pytest.mark.django_db
def test_import_reuses_existing_warehouse_and_location(products):
    warehouse = WarehouseFactory(name="Main")
    location = WarehouseLocationFactory(code="AA-01-00", warehouse=warehouse)

    summary = StockImportService("Main").import_from_json(
        _payload(_place("AA-01-00", ("P-1", 1)))
    )

    assert not summary.warehouse_created
    assert (summary.locations_created, summary.locations_existing) == (0, 1)
    assert WarehouseLocation.objects.count() == 1
    assert location.items.count() == 1


@pytest.mark.django_db
def test_import_accepts_list_of_warehouses(products):
    raw = json.dumps(
        [
            json.loads(_payload(_place("L-1", ("P-1", 1)))),
            json.loads(_payload(_place("L-2", ("P-2", 2)))),
        ]
    )

    summary = StockImportService("Main").import_from_json(raw)

    assert summary.items_created == 2


@pytest.mark.django_db
def test_import_ignores_json_warehouse_identity(products):
    StockImportService("Param").import_from_json(_payload(_place("L-1", ("P-1", 1))))

    assert list(Warehouse.objects.values_list("name", flat=True)) == ["Param"]


@pytest.mark.django_db
def test_unknown_product_raises_and_rolls_back(products):
    raw = _payload(
        _place("L-1", ("P-1", 1)),
        _place("L-2", ("NOPE-2", 1), ("NOPE-1", 1)),
    )

    with pytest.raises(DataImportError, match="NOPE-1, NOPE-2"):
        StockImportService("Main").import_from_json(raw)

    assert not Warehouse.objects.exists()
    assert not WarehouseLocation.objects.exists()
    assert not WarehouseItem.objects.exists()


@pytest.mark.django_db
def test_location_in_other_warehouse_raises_and_rolls_back(products):
    WarehouseLocationFactory(code="L-2", warehouse=WarehouseFactory(name="Other"))
    raw = _payload(_place("L-1", ("P-1", 1)), _place("L-2", ("P-1", 1)))

    with pytest.raises(DataImportError, match="already belongs to warehouse 'Other'"):
        StockImportService("Main").import_from_json(raw)

    assert not Warehouse.objects.filter(name="Main").exists()
    assert not WarehouseItem.objects.exists()
    assert not WarehouseLocation.objects.filter(code="L-1").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "{}}",
        '{"WarehousePlaces": "x"}',
        '{"WarehousePlaces": [{"Name": "no code"}]}',
        '{"WarehousePlaces": [{"Code": ""}]}',
        '{"WarehousePlaces": [{"Code": "' + "X" * 51 + '"}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": [{"Value": 1}]}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": '
        '[{"StockProductCode": "P-1"}]}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": '
        '[{"StockProductCode": "P-1", "Value": -1}]}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": '
        '[{"StockProductCode": "P-1", "Value": "abc"}]}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": '
        '[{"StockProductCode": "P-1", "Value": 1.23456}]}]}',
        '{"WarehousePlaces": [{"Code": "L", "StockItems": '
        '[{"StockProductCode": "P-1", "Value": 12345678901}]}]}',
    ],
)
def test_invalid_input_raises(products, raw):
    with pytest.raises(DataImportError, match="Invalid input data"):
        StockImportService("Main").import_from_json(raw)

    assert not Warehouse.objects.exists()


@pytest.mark.django_db
def test_empty_places_creates_only_warehouse():
    summary = StockImportService("Main").import_from_json('{"WarehousePlaces": []}')

    assert summary.warehouse_created
    assert summary.items_created == 0


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_warehouse_name_rejected(name):
    with pytest.raises(DataImportError, match="must not be empty"):
        StockImportService(name)


@pytest.mark.django_db
def test_missing_file_raises():
    with pytest.raises(DataImportError, match="Cannot read"):
        StockImportService("Main").import_from_path("/nonexistent/stock.json")


@pytest.mark.django_db
def test_command_imports_file(products, tmp_path, capsys):
    path = tmp_path / "stock.json"
    path.write_text(_payload(_place("L-1", ("P-1", 2))), encoding="utf-8-sig")

    call_command("import_warehouse_stock", file=str(path), warehouse="Main")

    assert WarehouseItem.objects.get().location.warehouse.name == "Main"
    assert "1 items" in capsys.readouterr().out


@pytest.mark.django_db
def test_command_turns_import_error_into_command_error(products, tmp_path):
    path = tmp_path / "stock.json"
    path.write_text(_payload(_place("L-1", ("NOPE", 2))))

    with pytest.raises(CommandError, match="NOPE"):
        call_command("import_warehouse_stock", file=str(path), warehouse="Main")


@pytest.mark.django_db
def test_import_accepts_bare_list_of_places(products):
    raw = json.dumps([_place("L-1", ("P-1", 1)), _place("L-2", ("P-2", 2))])

    summary = StockImportService("Main").import_from_json(raw)

    assert (summary.locations_created, summary.items_created) == (2, 2)


@pytest.mark.django_db
@pytest.mark.parametrize("raw", ["{}", '{"Code": "C"}', "null", "[null]", "5"])
def test_payload_without_places_is_rejected_not_silently_ignored(products, raw):
    with pytest.raises(DataImportError, match="Invalid input data"):
        StockImportService("Main").import_from_json(raw)

    assert not Warehouse.objects.exists()


def test_too_long_warehouse_name_rejected():
    with pytest.raises(DataImportError, match="too long"):
        StockImportService("W" * 51)
