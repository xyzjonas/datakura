from ninja.testing import TestClient

from apps.warehouse.api.routes.invoice_payment_methods import routes
from apps.warehouse.tests.factories.order import InvoicePaymentMethodFactory


def test_get_invoice_payment_methods_with_search(db) -> None:
    client = TestClient(routes)
    matching = InvoicePaymentMethodFactory.it(name="Bank transfer")
    InvoicePaymentMethodFactory.it(name="Cash")

    res = client.get("/?search_term=bank")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == matching.id
    assert data[0]["name"] == "Bank transfer"


def test_create_invoice_payment_method(db) -> None:
    client = TestClient(routes)

    res = client.post("/", json={"name": "Card"})

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Card"


def test_update_invoice_payment_method(db) -> None:
    client = TestClient(routes)
    method = InvoicePaymentMethodFactory.it(name="Cash")

    res = client.put(f"/{method.id}", json={"name": "Cash on delivery"})

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Cash on delivery"


def test_delete_invoice_payment_method(db) -> None:
    client = TestClient(routes)
    method = InvoicePaymentMethodFactory.it()

    res = client.delete(f"/{method.id}")

    assert res.status_code == 200
    assert res.json()["success"] is True
