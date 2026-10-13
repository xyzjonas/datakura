from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
import factory
from factory.django import DjangoModelFactory

DEFAULT_PASSWORD = "Secret-pass-123"
# hashed once - hashing per user would slow the test suite down
DEFAULT_PASSWORD_HASH = make_password(DEFAULT_PASSWORD)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.LazyFunction(lambda: DEFAULT_PASSWORD_HASH)

    class Params:
        superuser = factory.Trait(is_superuser=True, is_staff=True)
