"""
Slot Manager — Управление расписанием и слотами.
Использует SQLAlchemy + SQLite для хранения данных.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError

from database import Booking, Database, Service, WorkHours


class SlotManager:
    """Менеджер слотов и записей."""

    def __init__(self, db_path: str = "slot_magic.db"):
        self.db = Database(db_path)
        self.db.init_default_services()
        self.db.init_default_work_hours()

    def get_services(self) -> list:
        """Список услуг."""
        with self.db.get_session() as session:
            services = session.query(Service).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "duration_minutes": s.duration_minutes,
                    "price": s.price,
                    "description": s.description,
                }
                for s in services
            ]

    def get_service(self, service_id: str) -> Optional[dict]:
        """Получить услугу по ID."""
        with self.db.get_session() as session:
            service = session.query(Service).filter(Service.id == service_id).first()
            if not service:
                return None
            return {
                "id": service.id,
                "name": service.name,
                "duration_minutes": service.duration_minutes,
                "price": service.price,
                "description": service.description,
            }

    def get_available_slots(self, date: str, service_id: str) -> list:
        """Получить доступные слоты на дату для услуги."""
        service = self.get_service(service_id)
        if not service:
            return []

        with self.db.get_session() as session:
            # Проверяем рабочий день
            day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A").lower()
            work_day = (
                session.query(WorkHours).filter(WorkHours.day_name == day_name).first()
            )
            if not work_day or not work_day.is_active:
                return []

            # Генерируем слоты
            start_time = work_day.start_time
            end_time = work_day.end_time
            duration = service["duration_minutes"]

            available = []
            current = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")

            while current + timedelta(minutes=duration) <= end:
                time_str = current.strftime("%H:%M")

                # Проверяем не занят ли слот
                is_booked = (
                    session.query(Booking)
                    .filter(
                        Booking.date == date,
                        Booking.time == time_str,
                        Booking.status == "confirmed",
                    )
                    .first()
                    is not None
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
    ) -> Optional[dict]:
        """Создать запись."""
        # Проверяем доступность
        available = self.get_available_slots(date, service_id)
        if time not in available:
            return None

        # Генерируем ID
        booking_id = f"{date}_{time}_{service_id}_{client_telegram_id}"

        with self.db.get_session() as session:
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
                created_at=datetime.now(),
            )
            session.add(booking)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return None  # Слот уже занят (race condition protection)

            return {
                "id": booking.id,
                "service_id": booking.service_id,
                "date": booking.date,
                "time": booking.time,
                "client_name": booking.client_name,
                "client_phone": booking.client_phone,
                "client_telegram_id": booking.client_telegram_id,
                "status": booking.status,
            }

    def cancel_booking(self, booking_id: str, client_telegram_id: int) -> bool:
        """Отменить запись (только свою)."""
        with self.db.get_session() as session:
            booking = session.query(Booking).filter(Booking.id == booking_id).first()
            if not booking:
                return False
            # IDOR protection: проверяем владельца
            if booking.client_telegram_id != client_telegram_id:
                return False
            booking.status = "cancelled"
            session.commit()
            return True

    def get_client_bookings(self, client_telegram_id: int) -> list:
        """Записи клиента."""
        with self.db.get_session() as session:
            bookings = (
                session.query(Booking)
                .filter(
                    Booking.client_telegram_id == client_telegram_id,
                    Booking.status == "confirmed",
                )
                .all()
            )
            return [
                {
                    "id": b.id,
                    "service_id": b.service_id,
                    "date": b.date,
                    "time": b.time,
                    "client_name": b.client_name,
                    "client_phone": b.client_phone,
                    "client_telegram_id": b.client_telegram_id,
                    "status": b.status,
                }
                for b in bookings
            ]

    def get_all_bookings(self, date: str = None) -> list:
        """Все записи (для админки)."""
        with self.db.get_session() as session:
            query = session.query(Booking).filter(Booking.status == "confirmed")
            if date:
                query = query.filter(Booking.date == date)
            bookings = query.all()
            return [
                {
                    "id": b.id,
                    "service_id": b.service_id,
                    "date": b.date,
                    "time": b.time,
                    "client_name": b.client_name,
                    "client_phone": b.client_phone,
                    "client_telegram_id": b.client_telegram_id,
                    "status": b.status,
                }
                for b in bookings
            ]

    def get_bookings_needing_reminder(
        self, hours_before: int, now: datetime | None = None
    ) -> list:
        """Записи которым нужно отправить напоминание."""
        now = now or datetime.now()

        need_reminder = []
        with self.db.get_session() as session:
            bookings = (
                session.query(Booking).filter(Booking.status == "confirmed").all()
            )

            for b in bookings:
                booking_datetime = datetime.strptime(
                    f"{b.date} {b.time}", "%Y-%m-%d %H:%M"
                )

                # Проверяем что запись через ~hours_before часов
                diff = (booking_datetime - now).total_seconds() / 3600

                if diff <= hours_before + 0.5 and diff >= hours_before - 0.5:
                    if hours_before == 24 and not b.reminder_sent_24h:
                        b.reminder_sent_24h = True
                        session.commit()
                        need_reminder.append(
                            {
                                "id": b.id,
                                "service_id": b.service_id,
                                "date": b.date,
                                "time": b.time,
                                "client_telegram_id": b.client_telegram_id,
                            }
                        )
                    elif hours_before == 2 and not b.reminder_sent_2h:
                        b.reminder_sent_2h = True
                        session.commit()
                        need_reminder.append(
                            {
                                "id": b.id,
                                "service_id": b.service_id,
                                "date": b.date,
                                "time": b.time,
                                "client_telegram_id": b.client_telegram_id,
                            }
                        )

        return need_reminder
