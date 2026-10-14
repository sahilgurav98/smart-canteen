
import os
import tempfile

import pytest
import app as module


@pytest.fixture()
def client(monkeypatch):
    """Create an isolated test database and Flask client."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    original_db_path = module.DB_PATH
    original_secret_key = module.app.secret_key
    original_admin_password = module.ADMIN_PASSWORD
    original_testing = module.app.config.get("TESTING", False)

    module.DB_PATH = db_path
    module.app.secret_key = "test-secret"
    module.ADMIN_PASSWORD = "test-password"
    module.app.config["TESTING"] = True

    try:
        module.init_db()

        with module.app.test_client() as test_client:
            yield test_client

    finally:
        module.DB_PATH = original_db_path
        module.app.secret_key = original_secret_key
        module.ADMIN_PASSWORD = original_admin_password
        module.app.config["TESTING"] = original_testing

        if os.path.exists(db_path):
            os.remove(db_path)


def test_homepage_and_menu(client):
    """Homepage and menu API should load successfully."""
    assert client.get("/").status_code == 200

    response = client.get("/api/menu")
    assert response.status_code == 200
    assert len(response.get_json()) >= 6


def test_order_total_and_tracking(client):
    """Orders should calculate the total and expose tracking status."""
    response = client.post(
        "/api/orders",
        json={
            "pickup_time": "As soon as possible",
            "items": [{"id": "snack2", "quantity": 2}],
        },
    )

    assert response.status_code == 201

    order = response.get_json()
    assert order["total"] == 60

    tracking = client.get(f'/api/orders/{order["id"]}')
    assert tracking.status_code == 200
    assert tracking.get_json()["status"] == "Pending"


def test_empty_cart_is_rejected(client):
    """An empty cart should be rejected with HTTP 400."""
    response = client.post(
        "/api/orders",
        json={"items": []},
    )

    assert response.status_code == 400


def test_admin_orders_require_login(client):
    """Admin order data must not be available without authentication."""
    response = client.get("/api/admin/orders")
    assert response.status_code == 401


def test_admin_can_update_order_status(client):
    """An authenticated admin can change an order's status."""
    order_response = client.post(
        "/api/orders",
        json={
            "pickup_time": "In 15 minutes",
            "items": [{"id": "snack2", "quantity": 1}],
        },
    )

    assert order_response.status_code == 201
    order = order_response.get_json()

    login_response = client.post(
        "/admin/login",
        data={"password": "test-password"},
        follow_redirects=False,
    )

    assert login_response.status_code == 302

    with client.session_transaction() as session:
        assert session.get("admin") is True

    response = client.patch(
        f'/api/admin/orders/{order["id"]}',
        json={"status": "Preparing"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "Preparing"
