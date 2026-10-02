from importlib import import_module

import pytest
from django.apps import apps
from django.db import connection

from apps.warehouse.models.customer import GHOST_CUSTOMER_ID, Customer
from apps.warehouse.tests.factories.customer import CustomerFactory

migration = import_module("apps.warehouse.migrations.0081_move_ghost_customer")


@pytest.mark.django_db
def test_ghost_customer_gets_highest_possible_id():
    assert Customer.get_ghost_customer() == GHOST_CUSTOMER_ID == 2**31 - 1
    assert Customer.get_ghost_customer() == GHOST_CUSTOMER_ID  # idempotent
    assert Customer.objects.filter(code="ghost-customer").count() == 1


@pytest.mark.django_db
def test_low_ids_stay_free_for_legacy_customers():
    Customer.get_ghost_customer()

    assert not Customer.objects.filter(pk=1).exists()
    assert CustomerFactory(id=1).pk == 1


@pytest.mark.django_db
def test_migration_moves_legacy_ghost_and_keeps_its_references():
    from apps.warehouse.tests.factories.order import InboundOrderFactory

    Customer.objects.filter(code="ghost-customer").delete()
    ghost = CustomerFactory(id=1, code="ghost-customer", name="N/A")
    order = InboundOrderFactory(customer=ghost)

    with connection.constraint_checks_disabled():
        migration.move_ghost_customer(apps, None)
    connection.check_constraints()

    order.refresh_from_db()
    assert order.customer_id == GHOST_CUSTOMER_ID
    assert not Customer.objects.filter(pk=1).exists()


@pytest.mark.django_db
def test_migration_without_ghost_or_already_moved_is_noop():
    migration.move_ghost_customer(apps, None)
    Customer.get_ghost_customer()
    migration.move_ghost_customer(apps, None)

    assert Customer.objects.filter(pk=GHOST_CUSTOMER_ID).count() == 1
