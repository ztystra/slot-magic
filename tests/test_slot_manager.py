"""
Unit tests for Slot Manager.
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from slot_manager import SlotManager


@pytest.fixture
def manager():
    """Создать менеджер с тестовой БД."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    manager = SlotManager(db_path)
    yield manager

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def manager_with_bookings(manager):
    """Менеджер с тестовыми записями."""
    # Создаём запись на завтрашний день
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    manager.create_booking(
        service_id="haircut",
        date=tomorrow,
        time="10:00",
        client_name="Тест Клиент",
        client_phone="79991234567",
        client_telegram_id=123456789,
    )
    return manager


class TestServices:
    """Тесты услуг."""

    def test_get_services(self, manager):
        """Получить список услуг."""
        services = manager.get_services()
        assert len(services) > 0
        assert any(s["id"] == "haircut" for s in services)

    def test_get_service(self, manager):
        """Получить конкретную услугу."""
        service = manager.get_service("haircut")
        assert service is not None
        assert service["name"] == "Стрижка"
        assert service["duration_minutes"] == 30
        assert service["price"] == 800

    def test_get_service_not_found(self, manager):
        """Услуга не найдена."""
        service = manager.get_service("nonexistent")
        assert service is None


class TestAvailableSlots:
    """Тесты доступных слотов."""

    def test_get_available_slots(self, manager):
        """Получить доступные слоты на день."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = manager.get_available_slots(tomorrow, "haircut")
        assert len(slots) > 0
        assert "10:00" in slots

    def test_get_slots_no_bookings(self, manager):
        """Слоты без записей."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = manager.get_available_slots(tomorrow, "haircut")
        # Должно быть много слотов (9:00-19:00, шаг 30 мин)
        assert len(slots) >= 15

    def test_get_slots_with_booking(self, manager_with_bookings):
        """Слоты с занятой записью."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = manager_with_bookings.get_available_slots(tomorrow, "haircut")
        # 10:00 должен быть занят
        assert "10:00" not in slots

    def test_get_slots_sunday(self, manager):
        """В воскресенье нет слотов."""
        # Находим ближайшее воскресенье
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        sunday = today + timedelta(days=days_until_sunday)
        sunday_str = sunday.strftime("%Y-%m-%d")

        slots = manager.get_available_slots(sunday_str, "haircut")
        assert len(slots) == 0

    def test_get_slots_invalid_service(self, manager):
        """Несуществующая услуга."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = manager.get_available_slots(tomorrow, "nonexistent")
        assert len(slots) == 0


class TestBookings:
    """Тесты записей."""

    def test_create_booking(self, manager):
        """Создать запись."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        booking = manager.create_booking(
            service_id="haircut",
            date=tomorrow,
            time="10:00",
            client_name="Иван",
            client_phone="79991234567",
            client_telegram_id=123456789,
        )
        assert booking is not None
        assert booking["status"] == "confirmed"
        assert booking["client_name"] == "Иван"

    def test_create_booking_conflict(self, manager_with_bookings):
        """Запись на занятый слот."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        booking = manager_with_bookings.create_booking(
            service_id="haircut",
            date=tomorrow,
            time="10:00",  # Уже занято
            client_name="Другой",
            client_phone="79997654321",
            client_telegram_id=987654321,
        )
        assert booking is None

    def test_cancel_booking(self, manager_with_bookings):
        """Отменить запись."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        bookings = manager_with_bookings.get_client_bookings(123456789)
        assert len(bookings) == 1

        result = manager_with_bookings.cancel_booking(bookings[0]["id"])
        assert result is True

        # Проверяем что запись отменена
        bookings = manager_with_bookings.get_client_bookings(123456789)
        assert len(bookings) == 0

    def test_cancel_booking_not_found(self, manager):
        """Отменить несуществующую запись."""
        result = manager.cancel_booking("nonexistent")
        assert result is False

    def test_get_client_bookings(self, manager_with_bookings):
        """Получить записи клиента."""
        bookings = manager_with_bookings.get_client_bookings(123456789)
        assert len(bookings) == 1
        assert bookings[0]["client_name"] == "Тест Клиент"

    def test_get_client_bookings_empty(self, manager):
        """Записи клиента пусты."""
        bookings = manager.get_client_bookings(999999999)
        assert len(bookings) == 0

    def test_get_all_bookings(self, manager_with_bookings):
        """Все записи."""
        bookings = manager_with_bookings.get_all_bookings()
        assert len(bookings) == 1

    def test_get_all_bookings_by_date(self, manager_with_bookings):
        """Все записи на дату."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        bookings = manager_with_bookings.get_all_bookings(date=tomorrow)
        assert len(bookings) == 1

        bookings = manager_with_bookings.get_all_bookings(date="2099-01-01")
        assert len(bookings) == 0


class TestReminders:
    """Тесты напоминаний."""

    def test_get_bookings_needing_reminder(self, manager):
        """Записи для напоминания."""
        # Создаём запись на текущий час (примерно через 2 часа)
        now = datetime.now()
        target_time = now + timedelta(hours=2)
        target_date = target_time.strftime("%Y-%m-%d")
        target_hour = target_time.strftime("%H:00")

        # Создаём запись (если слот доступен)
        available = manager.get_available_slots(target_date, "haircut")
        if target_hour in available:
            manager.create_booking(
                service_id="haircut",
                date=target_date,
                time=target_hour,
                client_name="Тест",
                client_phone="79990000000",
                client_telegram_id=111111111,
            )

            reminders = manager.get_bookings_needing_reminder(2)
            assert len(reminders) > 0
