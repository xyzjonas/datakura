import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.currency import CURRENCY_CHOICES
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    OutboundCalculation,
    OutboundCalculationItem,
    OutboundCalculationState,
    OutboundOrder,
    OutboundOrderState,
    OutboundOrderItem,
    CreditNoteToSupplier,
    Invoice,
    InvoicePaymentMethod,
)
from apps.warehouse.models.shipping import OutboundOrderShipping, ShippingType
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import StockProductFactory


class InboundOrderItemFactory(DjangoModelFactory):
    """Factory for InboundOrderItem model"""

    class Meta:
        model = InboundOrderItem

    @classmethod
    def it(cls, **kwargs) -> InboundOrderItem:
        return cls(**kwargs)  # type: ignore

    stock_product = factory.SubFactory(StockProductFactory)
    amount = factory.Faker("random_int", min=1, max=100, step=1)
    order = None
    index = factory.LazyAttribute(lambda o: o.order.items.count() if o.order else 0)
    unit_price = factory.Faker("random_int", min=1, max=200, step=1)
    total_price = factory.LazyAttribute(lambda o: o.amount * o.unit_price)


class InboundOrderFactory(DjangoModelFactory):
    """Factory for InboundOrder model"""

    class Meta:
        model = InboundOrder
        django_get_or_create = ("code",)

    @classmethod
    def it(cls, **kwargs) -> InboundOrder:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"ORD-{n:04d}")
    external_code = factory.Sequence(lambda n: f"EXT-{n:12d}")
    description = factory.Faker("text", max_nb_chars=50)
    note = factory.Faker("text", max_nb_chars=200)

    supplier = factory.SubFactory(CustomerFactory)
    currency = CURRENCY_CHOICES[0][0]
    invoice = None


class OutboundOrderItemFactory(DjangoModelFactory):
    """Factory for OutboundOrderItem model"""

    class Meta:
        model = OutboundOrderItem

    @classmethod
    def it(cls, **kwargs) -> OutboundOrderItem:
        return cls(**kwargs)  # type: ignore

    stock_product = factory.SubFactory(StockProductFactory)
    amount = factory.Faker("random_int", min=1, max=100, step=1)
    order = None
    index = factory.LazyAttribute(lambda o: o.order.items.count() if o.order else 0)
    unit_price = factory.Faker("random_int", min=1, max=200, step=1)
    total_price = factory.LazyAttribute(lambda o: o.amount * o.unit_price)
    desired_package_type = None
    desired_batch = None


class OutboundOrderFactory(DjangoModelFactory):
    """Factory for OutboundOrder model"""

    class Meta:
        model = OutboundOrder
        django_get_or_create = ("code",)

    @classmethod
    def it(cls, **kwargs) -> OutboundOrder:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"SORD-{n:04d}")
    external_code = factory.Sequence(lambda n: f"SEXT-{n:12d}")
    description = factory.Faker("text", max_nb_chars=50)
    note = factory.Faker("text", max_nb_chars=200)

    customer = factory.SubFactory(CustomerFactory)
    currency = CURRENCY_CHOICES[0][0]
    invoice = None
    state = OutboundOrderState.SUBMITTED


class OutboundCalculationItemFactory(DjangoModelFactory):
    """Factory for OutboundCalculationItem model"""

    class Meta:
        model = OutboundCalculationItem

    @classmethod
    def it(cls, **kwargs) -> OutboundCalculationItem:
        return cls(**kwargs)  # type: ignore

    stock_product = factory.SubFactory(StockProductFactory)
    amount = factory.Faker("random_int", min=1, max=100, step=1)
    calculation = None
    index = factory.LazyAttribute(
        lambda o: o.calculation.items.count() if o.calculation else 0
    )
    unit_price = factory.Faker("random_int", min=1, max=200, step=1)
    total_price = factory.LazyAttribute(lambda o: o.amount * o.unit_price)
    desired_package_type = None
    desired_batch = None


class OutboundCalculationFactory(DjangoModelFactory):
    """Factory for OutboundCalculation model"""

    class Meta:
        model = OutboundCalculation
        django_get_or_create = ("code",)

    @classmethod
    def it(cls, **kwargs) -> OutboundCalculation:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"KCALC-{n:04d}")
    external_code = factory.Sequence(lambda n: f"CEXT-{n:12d}")
    description = factory.Faker("text", max_nb_chars=50)
    note = factory.Faker("text", max_nb_chars=200)

    customer = factory.SubFactory(CustomerFactory)
    currency = CURRENCY_CHOICES[0][0]
    state = OutboundCalculationState.OPEN
    order = None
    is_deleted = False


class CreditNoteSupplierFactory(DjangoModelFactory):
    """Factory for CreditNoteSupplier model"""

    class Meta:
        model = CreditNoteToSupplier
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"ORD-{n:04d}")
    reason = factory.Faker("text", max_nb_chars=50)
    note = factory.Faker("text", max_nb_chars=200)

    order = factory.SubFactory(InboundOrderFactory)


class InvoicePaymentMethodFactory(DjangoModelFactory):
    class Meta:
        model = InvoicePaymentMethod
        django_get_or_create = ("name",)

    @classmethod
    def it(cls, **kwargs) -> InvoicePaymentMethod:
        return cls(**kwargs)  # type: ignore

    name = factory.Sequence(lambda n: f"Payment Method {n:04d}")


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice
        django_get_or_create = ("code",)

    @classmethod
    def it(cls, **kwargs) -> Invoice:
        return cls(**kwargs)  # type: ignore

    customer = factory.SubFactory(CustomerFactory)
    supplier = factory.SubFactory(CustomerFactory)
    code = factory.Sequence(lambda n: f"INV-{n:04d}")
    issued_date = factory.Faker("date_object")
    due_date = factory.Faker("date_object")
    payment_method = factory.SubFactory(InvoicePaymentMethodFactory)
    external_code = factory.Sequence(lambda n: f"EINV-{n:04d}")
    taxable_supply_date = factory.Faker("date_object")
    paid_date = None
    currency = CURRENCY_CHOICES[0][0]
    note = factory.Faker("text", max_nb_chars=200)


class ShippingTypeFactory(DjangoModelFactory):
    class Meta:
        model = ShippingType
        django_get_or_create = ("name",)

    @classmethod
    def it(cls, **kwargs) -> ShippingType:
        return cls(**kwargs)  # type: ignore

    name = factory.Sequence(lambda n: f"Shipping Type {n:04d}")


class OutboundOrderShippingFactory(DjangoModelFactory):
    """The order already has an (empty) shipping, created with it: update that one."""

    class Meta:
        model = OutboundOrderShipping

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        order = kwargs.pop("order")
        return model_class.objects.update_or_create(order=order, defaults=kwargs)[0]

    @classmethod
    def it(cls, **kwargs) -> OutboundOrderShipping:
        return cls(**kwargs)  # type: ignore

    order = factory.SubFactory(OutboundOrderFactory)
    shipping_type = factory.SubFactory(ShippingTypeFactory)
    package_number = ""
    name = factory.Faker("name")
    state = "CZ"
    city = factory.Faker("city")
    street = factory.Faker("street_address")
    postal_code = "78401"
    email = factory.Faker("email")
    phone = "+420 770 181 044"
