"""
Database models for Slot-Magic using SQLAlchemy + SQLite.
"""

from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Service(Base):
    """Услуга."""

    __tablename__ = "services"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, default="")

    # Relationships
    bookings = relationship("Booking", back_populates="service")

    def __repr__(self):
        return f"<Service {self.name} ({self.duration_minutes}min, {self.price}₽)>"


class Booking(Base):
    """Запись клиента."""

    __tablename__ = "bookings"

    id = Column(String(200), primary_key=True)
    service_id = Column(String(50), ForeignKey("services.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time = Column(String(5), nullable=False)  # HH:MM
    client_name = Column(String(200), nullable=False)
    client_phone = Column(String(50), nullable=False)
    client_telegram_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, completed
    created_at = Column(DateTime, default=datetime.now)
    reminder_sent_24h = Column(Boolean, default=False)
    reminder_sent_2h = Column(Boolean, default=False)

    # Relationships
    service = relationship("Service", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.date} {self.time} - {self.client_name}>"


class WorkHours(Base):
    """Рабочие часы по дням недели."""

    __tablename__ = "work_hours"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day_name = Column(String(10), unique=True, nullable=False)  # monday, tuesday, etc.
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)  # HH:MM
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<WorkHours {self.day_name}: {self.start_time}-{self.end_time}>"


class Database:
    """Менеджер базы данных."""

    def __init__(self, db_path: str = "slot_magic.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        """Получить сессию."""
        return self.Session()

    def init_default_services(self):
        """Инициализировать услуги по умолчанию."""
        with self.get_session() as session:
            # Проверяем есть ли уже услуги
            if session.query(Service).count() > 0:
                return

            default_services = [
                Service(
                    id="haircut",
                    name="Стрижка",
                    duration_minutes=30,
                    price=800,
                    description="Мужская/женская стрижка",
                ),
                Service(
                    id="coloring",
                    name="Окрашивание",
                    duration_minutes=120,
                    price=3000,
                    description="Полное окрашивание волос",
                ),
                Service(
                    id="manicure",
                    name="Маникюр",
                    duration_minutes=60,
                    price=1200,
                    description="Классический маникюр",
                ),
                Service(
                    id="pedicure",
                    name="Педикюр",
                    duration_minutes=90,
                    price=1800,
                    description="Классический педикюр",
                ),
                Service(
                    id="shaving",
                    name="Бритьё",
                    duration_minutes=20,
                    price=500,
                    description="Классическое бритьё бороды",
                ),
                Service(
                    id="beard",
                    name="Оформление бороды",
                    duration_minutes=30,
                    price=600,
                    description="Подрезание и оформление",
                ),
                Service(
                    id="wash",
                    name="Мытьё + укладка",
                    duration_minutes=40,
                    price=900,
                    description="Мытьё и укладка волос",
                ),
                Service(
                    id="complex",
                    name="Комплекс",
                    duration_minutes=60,
                    price=1500,
                    description="Стрижка + мытьё + укладка",
                ),
            ]

            session.add_all(default_services)
            session.commit()

    def init_default_work_hours(self):
        """Инициализировать рабочие часы по умолчанию."""
        with self.get_session() as session:
            if session.query(WorkHours).count() > 0:
                return

            default_hours = [
                WorkHours(
                    day_name="monday",
                    start_time="09:00",
                    end_time="19:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="tuesday",
                    start_time="09:00",
                    end_time="19:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="wednesday",
                    start_time="09:00",
                    end_time="19:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="thursday",
                    start_time="09:00",
                    end_time="19:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="friday",
                    start_time="09:00",
                    end_time="19:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="saturday",
                    start_time="10:00",
                    end_time="17:00",
                    is_active=True,
                ),
                WorkHours(
                    day_name="sunday",
                    start_time="00:00",
                    end_time="00:00",
                    is_active=False,
                ),
            ]

            session.add_all(default_hours)
            session.commit()
