"""
Slot Manager — Управление расписанием и слотами.
Хранит расписание, клиентов, записи.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class Service:
    """Услуга."""

    id: str
    name: str
    duration_minutes: int
    price: float
    description: str = ""


@dataclass
class TimeSlot:
    """Временной слот."""

    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    service_id: str
    is_available: bool = True
    client_name: str = ""
    client_phone: str = ""


@dataclass
class Booking:
    """Запись."""

    id: str
    service_id: str
    date: str
    time: str
    client_name: str
    client_phone: str
    client_telegram_id: int
    status: str = "confirmed"  # confirmed, cancelled, completed
    created_at: str = ""
    reminder_sent_24h: bool = False
    reminder_sent_2h: bool = False


class SlotManager:
    """Менеджер слотов и записей."""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.services_file = self.data_dir / "services.json"
        self.slots_file = self.data_dir / "slots.json"
        self.bookings_file = self.data_dir / "bookings.json"
        self.work_hours_file = self.data_dir / "work_hours.json"

        self.services = self._load(self.services_file) or self._default_services()
        self.slots = self._load(self.slots_file) or []
        self.bookings = self._load(self.bookings_file) or []
        self.work_hours = self._load(self.work_hours_file) or self._default_work_hours()

    def _load(self, file: Path) -> Optional[list | dict]:
        """Загрузить данные из файла."""
        if file.exists():
            return json.loads(file.read_text(encoding="utf-8"))
        return None

    def _save(self, file: Path, data: list | dict):
        """Сохранить данные в файл."""
        file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _default_services(self) -> list:
        """Услуги по умолчанию."""
        services = [
            Service("haircut", "Стрижка", 30, 800, "Мужская/женская стрижка"),
            Service("coloring", "Окрашивание", 120, 3000, "Полное окрашивание волос"),
            Service("manicure", "Маникюр", 60, 1200, "Классический маникюр"),
            Service("pedicure", "Педикюр", 90, 1800, "Классический педикюр"),
            Service("shaving", "Бритьё", 20, 500, "Классическое бритьё бороды"),
            Service("beard", "Оформление бороды", 30, 600, "Подрезание и оформление"),
            Service("wash", "Мытьё + укладка", 40, 900, "Мытьё и укладка волос"),
            Service("complex", "Комплекс", 60, 1500, "Стрижка + мытьё + укладка"),
        ]
        self._save(self.services_file, [asdict(s) for s in services])
        return [asdict(s) for s in services]

    def _default_work_hours(self) -> dict:
        """Рабочие часы по умолчанию (пн-сб, 9:00-19:00)."""
        hours = {
            "monday": {"start": "09:00", "end": "19:00", "active": True},
            "tuesday": {"start": "09:00", "end": "19:00", "active": True},
            "wednesday": {"start": "09:00", "end": "19:00", "active": True},
            "thursday": {"start": "09:00", "end": "19:00", "active": True},
            "friday": {"start": "09:00", "end": "19:00", "active": True},
            "saturday": {"start": "10:00", "end": "17:00", "active": True},
            "sunday": {"start": "00:00", "end": "00:00", "active": False},
        }
        self._save(self.work_hours_file, hours)
        return hours

    def get_services(self) -> list:
        """Список услуг."""
        return self.services

    def get_service(self, service_id: str) -> Optional[dict]:
        """Получить услугу по ID."""
        for s in self.services:
            if s["id"] == service_id:
                return s
        return None

    def get_available_slots(self, date: str, service_id: str) -> list:
        """Получить доступные слоты на дату для услуги."""
        service = self.get_service(service_id)
        if not service:
            return []

        # Проверяем рабочий день
        day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A").lower()
        day_map = {
            "monday": "monday",
            "tuesday": "tuesday",
            "wednesday": "wednesday",
            "thursday": "thursday",
            "friday": "friday",
            "saturday": "saturday",
            "sunday": "sunday",
        }
        work_day = self.work_hours.get(day_map.get(day_name, ""), {})
        if not work_day.get("active", False):
            return []

        # Генерируем слоты
        start_time = work_day["start"]
        end_time = work_day["end"]
        duration = service["duration_minutes"]

        available = []
        current = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")

        while current + timedelta(minutes=duration) <= end:
            time_str = current.strftime("%H:%M")

            # Проверяем не занят ли слот
            is_booked = any(
                b["date"] == date
                and b["time"] == time_str
                and b["status"] == "confirmed"
                for b in self.bookings
            )

            if not is_booked:
                available.append(time_str)

            current += timedelta(minutes=30)  # шаг 30 минут

        return available

    def create_booking(
        self,
        service_id: str,
        date: str,
        time: str,
        client_name: str,
        client_phone: str,
        client_telegram_id: int,
    ) -> Optional[Booking]:
        """Создать запись."""
        # Проверяем доступность
        available = self.get_available_slots(date, service_id)
        if time not in available:
            return None

        # Генерируем ID
        booking_id = f"{date}_{time}_{service_id}_{client_telegram_id}"

        # Создаём запись
        booking = Booking(
            id=booking_id,
            service_id=service_id,
            date=date,
            time=time,
            client_name=client_name,
            client_phone=client_phone,
            client_telegram_id=client_telegram_id,
            status="confirmed",
            created_at=datetime.now().isoformat(),
        )

        self.bookings.append(asdict(booking))
        self._save(self.bookings_file, self.bookings)

        return booking

    def cancel_booking(self, booking_id: str) -> bool:
        """Отменить запись."""
        for b in self.bookings:
            if b["id"] == booking_id:
                b["status"] = "cancelled"
                self._save(self.bookings_file, self.bookings)
                return True
        return False

    def get_client_bookings(self, client_telegram_id: int) -> list:
        """Записи клиента."""
        return [
            b
            for b in self.bookings
            if b["client_telegram_id"] == client_telegram_id
            and b["status"] == "confirmed"
        ]

    def get_all_bookings(self, date: str = None) -> list:
        """Все записи (для админки)."""
        if date:
            return [
                b
                for b in self.bookings
                if b["date"] == date and b["status"] == "confirmed"
            ]
        return [b for b in self.bookings if b["status"] == "confirmed"]

    def get_bookings_needing_reminder(self, hours_before: int) -> list:
        """Записи которым нужно отправить напоминание."""
        now = datetime.now()

        need_reminder = []
        for b in self.bookings:
            if b["status"] != "confirmed":
                continue

            booking_datetime = datetime.strptime(
                f"{b['date']} {b['time']}", "%Y-%m-%d %H:%M"
            )

            # Проверяем что запись через ~hours_before часов
            diff = abs((booking_datetime - now).total_seconds() / 3600)

            if diff <= hours_before + 0.5 and diff >= hours_before - 0.5:
                if hours_before == 24 and not b.get("reminder_sent_24h"):
                    b["reminder_sent_24h"] = True
                    self._save(self.bookings_file, self.bookings)
                    need_reminder.append(b)
                elif hours_before == 2 and not b.get("reminder_sent_2h"):
                    b["reminder_sent_2h"] = True
                    self._save(self.bookings_file, self.bookings)
                    need_reminder.append(b)

        return need_reminder
