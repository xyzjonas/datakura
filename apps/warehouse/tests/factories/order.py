import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.currency import CURRENCY_CHOICES
from apps.warehouse.models.orders import IncomingOrder, IncomingOrderItem
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import StockProductFactory


class IncomingOrderItemFactory(DjangoModelFactory):
    """Factory for IncomingOrder model"""

    class Meta:
        model = IncomingOrderItem

    stock_product = factory.SubFactory(StockProductFactory)
    amount = factory.Faker("random_int", min=1, max=100, step=1)
    order = None
    unit_price = factory.Faker("random_int", min=1, max=200, step=1)


class IncomingOrderFactory(DjangoModelFactory):
    """Factory for IncomingOrder model"""

    class Meta:
        model = IncomingOrder
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"ORD-{n:04d}")
    external_code = factory.Sequence(lambda n: f"EXT-{n:12d}")
    description = factory.Faker("text", max_nb_chars=50)
    note = factory.Faker("text", max_nb_chars=200)

    supplier = factory.SubFactory(CustomerFactory)
    currency = CURRENCY_CHOICES[0][0]
