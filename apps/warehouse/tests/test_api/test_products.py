import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.product import routes


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_empty_db(db, client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data == {
        "count": 0,
        "data": [],
        "message": None,
        "success": True,
        "next": None,
        "previous": None,
    }
