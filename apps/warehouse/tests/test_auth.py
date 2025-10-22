import pytest
from django.contrib.auth.models import User


@pytest.fixture
def user():
    user = User.objects.create_user(username="john")
    return user


@pytest.mark.django_db
def test_hello(user):
    assert user.username == "john"
