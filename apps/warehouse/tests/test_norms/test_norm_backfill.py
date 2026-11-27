import pytest

from apps.warehouse.core.services.norm_backfill import norm_backfill_service
from apps.warehouse.models.product import Norm, NormType
from apps.warehouse.tests.factories.product import NormFactory, StockProductFactory

CUSTOMS = "CUSTOMS_DECLARATION_GROUP"

pytestmark = pytest.mark.django_db


def product(attributes: dict, **kwargs):
    return StockProductFactory(attributes=attributes, **kwargs)


def test_customs_group_and_norm_are_filled():
    p = product({CUSTOMS: " 73181590 ", "NORM": "DIN 84"})

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.customs_declaration_group == "73181590"
    assert (p.norm.type, p.norm.code) == ("DIN", "84")
    assert result.products_scanned == 1
    assert result.customs_filled == 1
    assert result.norms_linked == 1
    assert result.norms_created == 1
    assert result.without_customs == result.without_norm == 0
    assert result.invalid_count == 0


def test_din_is_default_and_others_become_aliases():
    p = product({"A": "ISO 1207", "B": "CSN_021131", "C": "DIN 84"})

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.norm.label == "DIN 84"
    assert {n.label for n in p.norm.equivalents.all()} == {"ISO 1207", "CSN 021131"}
    # the link is symmetric and also exists between the aliases themselves
    iso = Norm.objects.get(type=NormType.ISO)
    assert {n.label for n in iso.equivalents.all()} == {"DIN 84", "CSN 021131"}
    assert result.norms_created == 3
    assert result.aliases_linked == 3


def test_two_norms_of_one_type_are_not_aliased():
    p = product({"A": "DIN 84", "B": "DIN 85", "C": "ISO 1207"})

    norm_backfill_service.run()

    p.refresh_from_db()
    assert p.norm.label == "DIN 84"
    assert {n.label for n in p.norm.equivalents.all()} == {"ISO 1207"}
    assert not Norm.objects.get(code="85").equivalents.filter(type="DIN").exists()


def test_invalid_values_are_flagged_and_do_not_block_valid_ones():
    p = product({"A": "GOST 123", "B": "", "C": "DIN 933"})

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.norm.label == "DIN 933"
    assert result.invalid_count == 2
    assert {(i.product_code, i.key, i.value) for i in result.invalid} == {
        (p.code, "A", "GOST 123"),
        (p.code, "B", ""),
    }


def test_product_without_metas_is_reported_as_missing():
    product({})
    product({"color": "red"}, customs_declaration_group="1234")

    result = norm_backfill_service.run()

    assert result.products_scanned == 2
    assert result.without_norm == 2
    assert result.without_customs == 1
    assert result.invalid_count == 1  # "red" is no norm


def test_existing_values_are_never_overwritten():
    curated = NormFactory(type=NormType.CSN, code="999")
    p = product(
        {CUSTOMS: "111", "NORM": "DIN 84"},
        customs_declaration_group="222",
        norm=curated,
    )

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.customs_declaration_group == "222"
    assert p.norm == curated
    assert result.customs_filled == 0
    assert result.norms_linked == 0
    assert result.norms_kept == 1


def test_run_is_idempotent():
    product({CUSTOMS: "1", "A": "DIN 84", "B": "ISO 1207"})
    norm_backfill_service.run()

    second = norm_backfill_service.run()

    assert Norm.objects.count() == 2
    assert second.customs_filled == 0
    assert second.norms_created == 0
    assert second.aliases_linked == 0
    assert second.norms_kept == 1


def test_existing_catalogue_norm_is_reused():
    existing = NormFactory(type=NormType.DIN, code="84")
    p = product({"A": "DIN_84"})

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.norm == existing
    assert result.norms_created == 0


def test_products_share_norms():
    product({"A": "DIN 84"})
    product({"A": "din84"})

    result = norm_backfill_service.run()

    assert Norm.objects.count() == 1
    assert result.norms_linked == 2


@pytest.mark.parametrize("attributes", [{CUSTOMS: ""}, {CUSTOMS: "   "}])
def test_blank_customs_group_is_ignored(attributes):
    p = product(attributes)

    result = norm_backfill_service.run()

    p.refresh_from_db()
    assert p.customs_declaration_group is None
    assert result.customs_filled == 0
    assert result.invalid_count == 0


def test_progress_is_reported():
    from apps.warehouse.core.services.data_import.progress import ImportProgress

    for _ in range(3):
        product({})
    snapshots = []

    norm_backfill_service.run(ImportProgress(snapshots.append, min_interval=0))

    assert snapshots[-1].percent == 100
    assert any(s.stage_total == 3 and s.stage_done == 2 for s in snapshots)
