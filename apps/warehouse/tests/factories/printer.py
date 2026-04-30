import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.printer import Printer, UserAppSettings
from .user import UserFactory


class PrinterFactory(DjangoModelFactory):
    class Meta:
        model = Printer
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"PRINTER-{n:03d}")
    description = factory.Sequence(lambda n: f"Printer description {n}")


class UserAppSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserAppSettings

    user = factory.SubFactory(UserFactory)
    default_printer = factory.SubFactory(PrinterFactory)  # type: ignore[assignment]
