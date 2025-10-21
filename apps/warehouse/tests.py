from django.contrib.auth.models import User
from django.test import TestCase


# Create your tests here.
class TestCore(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="john")

    def test_hello(self):
        self.assertTrue(True)
