import copy
import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.product_import import (
    ProductImportService,
)
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.barcode import BarcodeType
from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.product import ProductGroup, ProductType, StockProduct
from apps.warehouse.models.product import StockProductPrice
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import StockProductFactory

SAMPLE = {
    "Id": 251635,
    "Code": "94-1801-10-160",
    "Name": "Závlačka ZB 10,0x160",
    "Note": "",
    "BuyPrice": 0,
    "ProductTypeCode": "GOODS",
    "ProductGroupCode": "KPZ",
    "UnitTypeCode": "100KS",
    "ProductMetas": [{"Code": "DIN_94", "Value": "DIN 94"}],
    "ProductPrices": [
        {
            "ProductPriceTypeCode": "NORMAL",
            "Price": 100000,
            "CurrencyCode": "",
            "UnitTypeCode": "100KS",
            "UnitCount": 1,
            "QuantityMin": None,
            "QuantityMax": None,
            "CustomerId": None,
        }
    ],
    "StockProduct": {
        "Code": "94-1801-10-160",
        "Name": "Závlačka ZB 10,0x160",
        "PartNumber": "",
        "Weight": 11.1,
        "Width": None,
        "StockBarCodes": [{"BarCode": "4441500020819", "Amount": None}],
    },
}


def sample(**overrides) -> dict:
    data = copy.deepcopy(SAMPLE)
    data.update(overrides)
    return data


def run(*rows: dict):
    return ProductImportService().import_from_json(json.dumps(list(rows)))


@pytest.mark.django_db
def test_import_sample_blank_database():
    summary = run(sample())

    assert (summary.created_count, summary.updated_count) == (1, 0)
    product = StockProduct.objects.get(code="94-1801-10-160")
    assert product.name == "Závlačka ZB 10,0x160"
    assert product.type.name == "Zboží"
    assert product.group and product.group.name == "KPZ"
    assert product.unit_of_measure.name == "100KS"
    assert product.unit_of_measure.base_uom.name == "KS"  # type: ignore[union-attr]
    assert product.unit_of_measure.amount_of_base_uom == 100
    assert product.unit_weight == Decimal("11.10")
    assert product.base_price == Decimal("100000.00")
    assert product.purchase_price == 0
    assert product.currency == "CZK"
    assert product.attributes == {"DIN_94": "DIN 94"}
    barcode = product.get_primary_barcode()
    assert barcode and barcode.code == "4441500020819"
    assert barcode.barcode_type == BarcodeType.EAN13


@pytest.mark.django_db
def test_import_is_idempotent_and_updates():
    run(sample())
    summary = run(sample(Name="Changed", BuyPrice=12.345))

    assert (summary.created_count, summary.updated_count) == (0, 1)
    assert StockProduct.objects.count() == 1
    assert ProductType.objects.count() == 1
    assert ProductGroup.objects.count() == 1
    assert UnitOfMeasure.objects.count() == 2
    product = StockProduct.objects.get()
    assert product.purchase_price == Decimal("12.35")
    assert len(product.get_barcodes()) == 1
    assert product.get_primary_barcode() is not None


@pytest.mark.django_db
def test_accepts_single_object():
    summary = ProductImportService().import_from_json(json.dumps(sample()))

    assert summary.created_count == 1


@pytest.mark.django_db
def test_product_without_stock_product_is_imported_with_blank_stock_fields():
    summary = run(sample(StockProduct=None))

    product = StockProduct.objects.get()
    assert (summary.created_count, summary.skipped_count) == (1, 0)
    assert summary.warnings == []
    assert product.code == SAMPLE["Code"]
    assert product.name == SAMPLE["Name"]
    assert product.unit_weight == 0
    assert product.get_barcodes().count() == 0


@pytest.mark.django_db
def test_service_product_is_imported_and_updated():
    service = {
        "Id": 264204,
        "Code": "ZINKOVÁNÍ",
        "Name": "ZINKOVÁNÍ",
        "Note": None,
        "BuyPrice": 0,
        "ProductTypeCode": "SERVICE",
        "ProductGroupCode": "",
        "UnitTypeCode": "ks",
        "ProductMetas": [],
        "ProductPrices": [],
        "StockProduct": None,
    }

    run(service)
    summary = run({**service, "Name": "Zinkování"})

    product = StockProduct.objects.get(code="ZINKOVÁNÍ")
    assert (summary.created_count, summary.updated_count) == (0, 1)
    assert product.name == "Zinkování"
    assert product.type.name == "SERVICE"
    assert product.group is None
    assert product.unit_of_measure.name == "KS"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "prices, expected_price, expected_currency",
    [
        ([], "0.00", "CZK"),
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 50, "CurrencyCode": "EUR",
           "UnitTypeCode": "100KS", "UnitCount": 1}], "50.00", "EUR"),
        # unit count divides
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 100, "CurrencyCode": "",
           "UnitTypeCode": "100KS", "UnitCount": 3}], "33.33", "CZK"),
        # non generic / non NORMAL prices are not the base price
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 50, "CustomerId": 5},
          {"ProductPriceTypeCode": "NORMAL", "Price": 50, "QuantityMin": 10},
          {"ProductPriceTypeCode": "SALE", "Price": 50}], "0.00", "CZK"),
        # price without a type is not the base price
        ([{"ProductPriceTypeCode": None, "Price": 50}, {"Price": 60}], "0.00", "CZK"),
        # missing unit count counts as 1
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 40, "UnitCount": None}],
         "40.00", "CZK"),
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 40, "UnitCount": ""}],
         "40.00", "CZK"),
        # blank price UoM is taken as the product UoM
        ([{"ProductPriceTypeCode": "NORMAL", "Price": 7, "UnitTypeCode": ""}],
         "7.00", "CZK"),
    ],
)  # fmt: skip
def test_base_price_selection(prices, expected_price, expected_currency):
    run(sample(ProductPrices=prices))

    product = StockProduct.objects.get()
    assert product.base_price == Decimal(expected_price)
    assert product.currency == expected_currency


@pytest.mark.django_db
def test_price_in_foreign_uom_is_ignored_with_warning():
    price = {"ProductPriceTypeCode": "NORMAL", "Price": 9, "UnitTypeCode": "KS"}

    summary = run(sample(ProductPrices=[price]))

    assert StockProduct.objects.get().base_price == 0
    assert "differs from product UoM" in summary.warnings[0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "uom, expected_name, base_name",
    [
        (None, "KS", None),
        ("", "KS", None),
        ("ks", "KS", None),
        ("100ks", "100KS", "KS"),
        ("kg", "KG", None),
        ("10 m", "10 M", "M"),
    ],
)
def test_unit_of_measure_mapping(uom, expected_name, base_name):
    run(sample(UnitTypeCode=uom, ProductPrices=[]))

    unit = StockProduct.objects.get().unit_of_measure
    assert unit.name == expected_name
    assert (unit.base_uom.name if unit.base_uom else None) == base_name


@pytest.mark.django_db
def test_existing_uom_is_reused():
    existing = UnitOfMeasure.objects.create(name="100KS")

    run(sample())

    assert StockProduct.objects.get().unit_of_measure == existing
    assert existing.base_uom is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, expected",
    [
        ("4441500020819", BarcodeType.EAN13),
        ("12345678", BarcodeType.EAN8),
        ("123456789012", BarcodeType.UPC),
        ("12345", BarcodeType.CUSTOM),
        ("ABC-1", BarcodeType.CUSTOM),
    ],
)
def test_barcode_type_detection(code, expected):
    stock = {**SAMPLE["StockProduct"], "StockBarCodes": [{"BarCode": code}]}

    run(sample(StockProduct=stock))

    assert StockProduct.objects.get().get_primary_barcode().barcode_type == expected  # type: ignore[union-attr]


@pytest.mark.django_db
def test_multiple_barcodes_first_is_primary_and_amount_is_ignored():
    stock = {
        **SAMPLE["StockProduct"],
        "StockBarCodes": [
            {"BarCode": "AAA", "Amount": None},
            {"BarCode": "BBB", "Amount": 100},
        ],
    }

    summary = run(sample(StockProduct=stock))

    product = StockProduct.objects.get()
    assert product.get_primary_barcode().code == "AAA"  # type: ignore[union-attr]
    assert len(product.get_barcodes()) == 2
    assert summary.barcodes_attached == 2
    assert summary.warnings == []


@pytest.mark.django_db
@pytest.mark.parametrize("amount", [None, 0, 1, -5, 100, "garbage", {"x": 1}, [1]])
def test_barcode_amount_is_never_validated(amount):
    stock = {
        **SAMPLE["StockProduct"],
        "StockBarCodes": [{"BarCode": "9760801160295", "Amount": amount}],
    }

    summary = run(sample(StockProduct=stock))

    assert summary.barcodes_attached == 1
    assert summary.warnings == []


@pytest.mark.django_db
def test_import_writes_audit_logs_for_create_and_update():
    run(sample())
    product = StockProduct.objects.get()
    log = AuditLog.objects.for_object(product).get()
    assert log.action == AuditAction.CREATE
    assert log.reason == AuditMessages.PRODUCT_IMPORTED.CS
    assert log.changes["name"] == {"old": "", "new": "Závlačka ZB 10,0x160"}
    assert log.changes["barcodes"]["new"] == "4441500020819"

    run(sample(Name="Renamed", StockProduct={**SAMPLE["StockProduct"], "Name": "New"}))

    log = AuditLog.objects.for_object(product).first()
    assert log.action == AuditAction.UPDATE  # type: ignore[union-attr]
    assert log.reason == AuditMessages.PRODUCT_UPDATED_BY_IMPORT.CS  # type: ignore[union-attr]
    assert log.changes == {  # type: ignore[union-attr]
        "name": {"old": "Závlačka ZB 10,0x160", "new": "New"}
    }


@pytest.mark.django_db
def test_reimport_of_unchanged_product_writes_no_audit_log():
    run(sample())
    run(sample())

    assert AuditLog.objects.count() == 1


@pytest.mark.django_db
def test_barcode_owned_by_other_product_is_skipped_with_warning():
    other = StockProductFactory()
    other.attach_barcode("4441500020819", is_primary=True)
    stock = {
        **SAMPLE["StockProduct"],
        "StockBarCodes": [{"BarCode": "4441500020819"}, {"BarCode": "FREE-1"}],
    }

    summary = run(sample(StockProduct=stock))

    product = StockProduct.objects.get(code=SAMPLE["Code"])
    assert [b.code for b in product.get_barcodes()] == ["FREE-1"]
    assert product.get_primary_barcode().code == "FREE-1"  # type: ignore[union-attr]
    assert other.get_primary_barcode().code == "4441500020819"  # type: ignore[union-attr]
    assert summary.barcodes_attached == 1
    assert "already belongs to another product" in summary.warnings[0]


@pytest.mark.django_db
def test_barcode_shared_inside_one_file_goes_to_first_product_only():
    def row(code):
        return sample(
            Code=code,
            StockProduct={"Code": code, "StockBarCodes": [{"BarCode": "SHARED"}]},
        )

    summary = run(row("A-1"), row("B-1"))

    assert (summary.created_count, summary.barcodes_attached) == (2, 1)
    assert StockProduct.objects.get(code="A-1").get_barcodes().count() == 1
    assert StockProduct.objects.get(code="B-1").get_barcodes().count() == 0
    assert "'B-1'" in summary.warnings[0]


@pytest.mark.django_db
def test_one_bad_row_rolls_back_all_and_reports_every_error():
    good = sample(Code="OK-1", StockProduct={**SAMPLE["StockProduct"], "Code": "OK-1"})
    mismatch = sample(StockProduct={**SAMPLE["StockProduct"], "Code": "OTHER"})
    bad_currency = sample(
        Code="CUR-1",
        StockProduct={"Code": "CUR-1", "StockBarCodes": []},
        ProductPrices=[{"ProductPriceTypeCode": "NORMAL", "Price": 1}],
    )
    bad_currency["ProductPrices"][0]["CurrencyCode"] = "XXX"

    with pytest.raises(DataImportError) as exc:
        run(good, mismatch, bad_currency)

    assert "Record #2" in str(exc.value)  # validation fails before any write
    assert not StockProduct.objects.exists()

    with pytest.raises(DataImportError, match="!= product code"):
        run(good, mismatch)
    assert not StockProduct.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw",
    [
        "nope",
        "[{]",
        "[1]",
        "[{}]",
        json.dumps([{**SAMPLE, "Code": ""}]),
        json.dumps([{**SAMPLE, "Name": None}]),
        json.dumps([{**SAMPLE, "ProductTypeCode": ""}]),
        json.dumps([{**SAMPLE, "Code": "x" * 256}]),
        json.dumps([{**SAMPLE, "StockProduct": {"Code": "a", "Weight": -1}}]),
        json.dumps([{**SAMPLE, "ProductMetas": [{"Value": "no code"}]}]),
        json.dumps(
            [
                {
                    **SAMPLE,
                    "ProductPrices": [
                        {"ProductPriceTypeCode": "NORMAL", "Price": 1, "UnitCount": 0}
                    ],
                }
            ]
        ),
    ],
)
def test_invalid_input_raises(raw):
    with pytest.raises(DataImportError):
        ProductImportService().import_from_json(raw)

    assert not StockProduct.objects.exists()


@pytest.mark.django_db
def test_price_overflowing_column_is_rejected():
    price = {"ProductPriceTypeCode": "NORMAL", "Price": 10**8, "UnitTypeCode": ""}

    with pytest.raises(DataImportError, match="does not fit"):
        run(sample(ProductPrices=[price]))

    assert not StockProduct.objects.exists()


@pytest.mark.django_db
def test_null_collections_and_blank_optionals_are_tolerated():
    run(
        sample(
            ProductGroupCode="",
            ProductMetas=None,
            ProductPrices=None,
            BuyPrice=None,
            StockProduct={
                "Code": "94-1801-10-160",
                "Weight": None,
                "StockBarCodes": None,
            },
        )
    )

    product = StockProduct.objects.get()
    assert product.group is None
    assert product.attributes == {}
    assert product.unit_weight == 0
    assert product.purchase_price == 0
    assert product.name == SAMPLE["Name"]


@pytest.mark.django_db
def test_missing_file_raises():
    with pytest.raises(DataImportError, match="Cannot read"):
        ProductImportService().import_from_path("/nonexistent/products.json")


@pytest.mark.django_db
def test_command_imports_file(tmp_path, capsys):
    path = tmp_path / "products.json"
    path.write_text(json.dumps([SAMPLE]), encoding="utf-8-sig")

    call_command("import_products", file=str(path))

    assert StockProduct.objects.count() == 1
    assert "1 created" in capsys.readouterr().out


@pytest.mark.django_db
def test_command_turns_import_error_into_command_error(tmp_path):
    path = tmp_path / "products.json"
    path.write_text("[{}]")

    with pytest.raises(CommandError):
        call_command("import_products", file=str(path))


@pytest.mark.django_db
def test_non_stock_service_product_with_negative_buy_price_is_imported():
    service = {
        "Id": 280106,
        "Code": "SLEVA",
        "Name": "SLEVA - prošlá expirace, zboží s vadou",
        "Note": None,
        "BuyPrice": -500,
        "ProductTypeCode": "SERVICE",
        "ProductGroupCode": "",
        "UnitTypeCode": "",
        "ProductMetas": [],
        "ProductPrices": [],
        "StockProduct": None,
    }

    summary = run(service, sample())

    assert (summary.skipped_count, summary.created_count) == (0, 2)
    assert StockProduct.objects.get(code="SLEVA").purchase_price == Decimal("-500.00")


@pytest.mark.django_db
def test_stock_product_with_negative_buy_price_is_imported():
    run(sample(BuyPrice=-500))

    assert StockProduct.objects.get().purchase_price == Decimal("-500.00")


@pytest.mark.django_db
@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_barcodes_are_dropped(blank):
    stock = {
        **SAMPLE["StockProduct"],
        "StockBarCodes": [{"BarCode": blank}, {"BarCode": "REAL-1"}, {"Amount": 3}],
    }

    summary = run(sample(StockProduct=stock))

    product = StockProduct.objects.get()
    assert [b.code for b in product.get_barcodes()] == ["REAL-1"]
    assert product.get_primary_barcode().code == "REAL-1"  # type: ignore[union-attr]
    assert summary.barcodes_attached == 1


def customer_price(customer_id, price=4900, **extra) -> dict:
    return {
        "ProductPriceTypeCode": "NORMAL",
        "Price": price,
        "CurrencyCode": "CZK",
        "UnitTypeCode": "100KS",
        "UnitCount": 1,
        "CustomerId": customer_id,
        **extra,
    }


@pytest.mark.django_db
def test_customer_price_is_stored_as_customer_override_not_base_price():
    customer = CustomerFactory()
    generic = {**customer_price(None, 575.39)}

    summary = run(sample(ProductPrices=[generic, customer_price(customer.pk)]))

    product = StockProduct.objects.get()
    assert product.base_price == Decimal("575.39")
    override = StockProductPrice.objects.get()
    assert (override.product, override.customer) == (product, customer)
    assert override.fixed_price == Decimal("4900.00")
    assert summary.warnings == []


@pytest.mark.django_db
@pytest.mark.parametrize("price_type", [None, "", "SALE", "NORMAL"])
def test_customer_price_ignores_price_type(price_type):
    customer = CustomerFactory()
    price = customer_price(customer.pk, ProductPriceTypeCode=price_type)

    summary = run(sample(ProductPrices=[price]))

    assert StockProductPrice.objects.get().customer == customer
    assert summary.warnings == []
    assert StockProduct.objects.get().base_price == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "product_uom, price_uom", [("KS", "ks"), ("ks", "KS"), ("100ks", "100KS")]
)
def test_uom_names_are_uppercased_for_creation_and_comparison(product_uom, price_uom):
    customer = CustomerFactory()
    prices = [
        {"ProductPriceTypeCode": "NORMAL", "Price": 7, "UnitTypeCode": price_uom},
        customer_price(customer.pk, 5, UnitTypeCode=price_uom),
    ]

    summary = run(sample(UnitTypeCode=product_uom, ProductPrices=prices))

    product = StockProduct.objects.get()
    assert product.unit_of_measure.name == product_uom.upper()
    assert product.base_price == Decimal("7.00")
    assert StockProductPrice.objects.get().fixed_price == Decimal("5.00")
    assert summary.warnings == []
    assert not UnitOfMeasure.objects.filter(name__regex=r"[a-z]").exists()


@pytest.mark.django_db
def test_customer_price_is_divided_by_unit_count_and_updated_on_reimport():
    customer = CustomerFactory()
    run(sample(ProductPrices=[customer_price(customer.pk, 100, UnitCount=3)]))
    assert StockProductPrice.objects.get().fixed_price == Decimal("33.33")

    run(sample(ProductPrices=[customer_price(customer.pk, 50)]))

    assert StockProductPrice.objects.get().fixed_price == Decimal("50.00")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "extra, reason",
    [
        ({"CustomerId": 999999}, "customer not found"),
        ({"UnitTypeCode": "KS"}, "differs from product UoM"),
    ],
)
def test_unusable_customer_price_is_skipped_with_warning(extra, reason):
    customer = CustomerFactory()
    price = {**customer_price(customer.pk), **extra}

    summary = run(sample(ProductPrices=[price]))

    assert not StockProductPrice.objects.exists()
    assert StockProduct.objects.count() == 1
    assert reason in summary.warnings[0]


@pytest.mark.django_db
def test_customer_prices_show_up_in_audit_log():
    customer = CustomerFactory(code="ACME")

    run(sample(ProductPrices=[customer_price(customer.pk)]))

    log = AuditLog.objects.for_object(StockProduct.objects.get()).get()
    assert log.changes["customer_prices"]["new"] == "ACME=4900.00"


@pytest.mark.django_db
def test_quantity_limited_customer_prices_are_stored_next_to_the_unlimited_one():
    customer = CustomerFactory(code="ACME")
    prices = [
        customer_price(customer.pk, 100),
        customer_price(customer.pk, 90, QuantityMin=10),
        customer_price(customer.pk, 80, QuantityMin=100),
    ]

    summary = run(sample(ProductPrices=prices))

    stored = {p.min_amount: p.fixed_price for p in StockProductPrice.objects.all()}
    assert stored == {
        None: Decimal("100.00"),
        Decimal("10"): Decimal("90.00"),
        Decimal("100"): Decimal("80.00"),
    }
    assert summary.warnings == []
    log = AuditLog.objects.for_object(StockProduct.objects.get()).get()
    assert (
        log.changes["customer_prices"]["new"]
        == "ACME=100.00, ACME from 10=90.00, ACME from 100=80.00"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("quantity_min", [None, 0, "0.0"])
def test_zero_or_missing_minimum_quantity_means_no_limit(quantity_min):
    customer = CustomerFactory()

    run(
        sample(ProductPrices=[customer_price(customer.pk, 5, QuantityMin=quantity_min)])
    )

    assert StockProductPrice.objects.get().min_amount is None


@pytest.mark.django_db
def test_quantity_limited_price_is_updated_on_reimport_and_not_duplicated():
    customer = CustomerFactory()
    run(sample(ProductPrices=[customer_price(customer.pk, 90, QuantityMin=10)]))

    run(sample(ProductPrices=[customer_price(customer.pk, 70, QuantityMin=10)]))

    price = StockProductPrice.objects.get()
    assert (price.min_amount, price.fixed_price) == (Decimal("10"), Decimal("70.00"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "extra, expected_min",
    [
        ({"QuantityMax": 10}, None),
        ({"QuantityMin": 5, "QuantityMax": 20}, Decimal("5")),
    ],
)
def test_maximum_quantity_is_ignored(extra, expected_min):
    customer = CustomerFactory()

    summary = run(sample(ProductPrices=[customer_price(customer.pk, 9, **extra)]))

    assert StockProductPrice.objects.get().min_amount == expected_min
    assert summary.warnings == []
