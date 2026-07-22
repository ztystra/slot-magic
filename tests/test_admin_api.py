"""Integration tests for the FastAPI admin panel."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from admin.main import create_app
from database import Booking
from slot_manager import SlotManager


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "admin.db"
    app = create_app(
        db_path=str(db_path),
        admin_username="owner",
        admin_password="strong-test-password",
        jwt_secret="test-secret-that-is-long-enough-for-jwt-signing",
    )
    with TestClient(app) as test_client:
        yield test_client, app.state.db


def login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "strong-test-password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_booking(
    db, *, booking_id="booking-1", service_id="haircut", status="confirmed"
):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    with db.get_session() as session:
        session.add(
            Booking(
                id=booking_id,
                service_id=service_id,
                date=tomorrow,
                time="10:00",
                client_name="Тест Клиент",
                client_phone="79991234567",
                client_telegram_id=123456789,
                status=status,
            )
        )
        session.commit()
    return tomorrow


def test_protected_endpoints_require_authentication(client):
    test_client, _ = client

    response = test_client.get("/api/bookings")

    assert response.status_code == 401


def test_login_rejects_wrong_password(client):
    test_client, _ = client

    response = test_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_admin_can_list_and_update_booking(client):
    test_client, db = client
    booking_date = add_booking(db)
    headers = login(test_client)

    listed = test_client.get(f"/api/bookings?date={booking_date}", headers=headers)
    updated = test_client.patch(
        "/api/bookings/booking-1/status",
        headers=headers,
        json={"status": "completed"},
    )

    assert listed.status_code == 200
    assert listed.json()[0]["client_name"] == "Тест Клиент"
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"


def test_booking_status_rejects_unknown_value(client):
    test_client, db = client
    add_booking(db)
    headers = login(test_client)

    response = test_client.patch(
        "/api/bookings/booking-1/status",
        headers=headers,
        json={"status": "deleted"},
    )

    assert response.status_code == 422


def test_reconfirming_an_occupied_slot_returns_conflict(client):
    test_client, db = client
    add_booking(db, booking_id="active-booking")
    add_booking(db, booking_id="cancelled-booking", status="cancelled")
    headers = login(test_client)

    response = test_client.patch(
        "/api/bookings/cancelled-booking/status",
        headers=headers,
        json={"status": "confirmed"},
    )

    assert response.status_code == 409


def test_admin_can_create_update_and_delete_service(client):
    test_client, _ = client
    headers = login(test_client)

    created = test_client.post(
        "/api/services",
        headers=headers,
        json={
            "id": "massage",
            "name": "Массаж",
            "duration_minutes": 60,
            "price": 2500,
            "description": "Общий массаж",
        },
    )
    updated = test_client.put(
        "/api/services/massage",
        headers=headers,
        json={"price": 2800},
    )
    deleted = test_client.delete("/api/services/massage", headers=headers)

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["price"] == 2800
    assert deleted.status_code == 200


def test_service_validation_rejects_bad_id_and_negative_price(client):
    test_client, _ = client
    headers = login(test_client)

    response = test_client.post(
        "/api/services",
        headers=headers,
        json={
            "id": "../../bad",
            "name": "Bad",
            "duration_minutes": 0,
            "price": -1,
        },
    )

    assert response.status_code == 422


def test_service_with_bookings_cannot_be_deleted(client):
    test_client, db = client
    add_booking(db)
    headers = login(test_client)

    response = test_client.delete("/api/services/haircut", headers=headers)

    assert response.status_code == 409


def test_service_with_cancelled_booking_cannot_be_deleted(client):
    test_client, db = client
    add_booking(db, status="cancelled")
    headers = login(test_client)

    response = test_client.delete("/api/services/haircut", headers=headers)

    assert response.status_code == 409


def test_stats_return_real_counts_and_popular_service(client):
    test_client, db = client
    add_booking(db)
    headers = login(test_client)

    response = test_client.get("/api/stats", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_bookings"] == 1
    assert body["popular_services"][0] == {
        "service_id": "haircut",
        "service_name": "Стрижка",
        "count": 1,
    }


def test_admin_can_update_work_hours(client):
    test_client, _ = client
    headers = login(test_client)

    response = test_client.put(
        "/api/work-hours/sunday",
        headers=headers,
        json={"start_time": "10:00", "end_time": "15:00", "is_active": True},
    )

    assert response.status_code == 200
    assert response.json() == {
        "day_name": "sunday",
        "start_time": "10:00",
        "end_time": "15:00",
        "is_active": True,
    }


def test_frontend_is_served(client):
    test_client, _ = client

    response = test_client.get("/")

    assert response.status_code == 200
    assert "Slot-Magic Admin" in response.text


def test_service_created_in_admin_is_visible_to_bot_layer(tmp_path):
    db_path = tmp_path / "shared.db"
    app = create_app(
        db_path=str(db_path),
        admin_username="owner",
        admin_password="strong-test-password",
        jwt_secret="test-secret-that-is-long-enough-for-jwt-signing",
    )

    with TestClient(app) as test_client:
        headers = login(test_client)
        response = test_client.post(
            "/api/services",
            headers=headers,
            json={
                "id": "shared_service",
                "name": "Общая услуга",
                "duration_minutes": 40,
                "price": 1700,
            },
        )

    manager = SlotManager(str(db_path))

    service = manager.get_service("shared_service")

    assert response.status_code == 201
    assert service is not None
    assert service["name"] == "Общая услуга"
