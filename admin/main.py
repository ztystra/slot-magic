"""FastAPI admin panel for Slot-Magic."""

import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from database import Booking, Database, Service, WorkHours

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
VALID_DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
FRONTEND_DIR = Path(__file__).parent / "frontend"
security = HTTPBearer(auto_error=False)


class AdminLogin(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class Token(BaseModel):
    access_token: str
    token_type: str


class BookingStatusUpdate(BaseModel):
    status: Literal["confirmed", "cancelled", "completed"]


class ServiceCreate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,49}$")
    name: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(gt=0, le=1440)
    price: float = Field(ge=0, le=100_000_000)
    description: str = Field(default="", max_length=2000)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    price: float | None = Field(default=None, ge=0, le=100_000_000)
    description: str | None = Field(default=None, max_length=2000)


class WorkHoursUpdate(BaseModel):
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    is_active: bool


def _create_access_token(username: str, secret: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": username, "type": "admin", "exp": expires_at},
        secret,
        algorithm=ALGORITHM,
    )


def _serialize_booking(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "service_id": booking.service_id,
        "date": booking.date,
        "time": booking.time,
        "client_name": booking.client_name,
        "client_phone": booking.client_phone,
        "client_telegram_id": booking.client_telegram_id,
        "status": booking.status,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
    }


def _serialize_service(service: Service) -> dict:
    return {
        "id": service.id,
        "name": service.name,
        "duration_minutes": service.duration_minutes,
        "price": service.price,
        "description": service.description or "",
    }


def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            request.app.state.jwt_secret,
            algorithms=[ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    username = payload.get("sub")
    if payload.get("type") != "admin" or username != request.app.state.admin_username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username


def create_app(
    db_path: str | None = None,
    admin_username: str | None = None,
    admin_password: str | None = None,
    jwt_secret: str | None = None,
) -> FastAPI:
    """Create a configured application; secrets have no unsafe defaults."""
    resolved_db_path = db_path or os.getenv("SQLITE_DB_PATH", "slot_magic.db")
    resolved_username = admin_username or os.getenv("ADMIN_USERNAME")
    resolved_password = admin_password or os.getenv("ADMIN_PASSWORD")
    resolved_secret = jwt_secret or os.getenv("JWT_SECRET")

    missing = [
        name
        for name, value in (
            ("ADMIN_USERNAME", resolved_username),
            ("ADMIN_PASSWORD", resolved_password),
            ("JWT_SECRET", resolved_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required admin settings: {', '.join(missing)}")
    if len(resolved_password) < 10:
        raise RuntimeError("ADMIN_PASSWORD must contain at least 10 characters")
    if len(resolved_secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")

    app = FastAPI(
        title="Slot-Magic Admin API",
        description="API для управления записями, услугами и рабочими часами",
        version="1.0.0",
    )

    app.state.db = Database(resolved_db_path)
    app.state.db.init_default_services()
    app.state.db.init_default_work_hours()
    app.state.admin_username = resolved_username
    app.state.admin_password = resolved_password
    app.state.jwt_secret = resolved_secret

    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.post("/api/auth/login", response_model=Token)
    async def login(admin: AdminLogin):
        username_matches = hmac.compare_digest(admin.username, app.state.admin_username)
        password_matches = hmac.compare_digest(admin.password, app.state.admin_password)
        if not username_matches or not password_matches:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        return {
            "access_token": _create_access_token(admin.username, app.state.jwt_secret),
            "token_type": "bearer",
        }

    @app.get("/api/bookings")
    async def get_bookings(
        date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
        booking_status: Literal["confirmed", "cancelled", "completed"] | None = Query(
            default="confirmed", alias="status"
        ),
        _admin: str = Depends(get_current_admin),
    ):
        with app.state.db.get_session() as session:
            query = session.query(Booking)
            if date:
                query = query.filter(Booking.date == date)
            if booking_status:
                query = query.filter(Booking.status == booking_status)
            bookings = query.order_by(Booking.date, Booking.time).all()
            return [_serialize_booking(booking) for booking in bookings]

    @app.get("/api/bookings/{booking_id}")
    async def get_booking(booking_id: str, _admin: str = Depends(get_current_admin)):
        with app.state.db.get_session() as session:
            booking = session.query(Booking).filter(Booking.id == booking_id).first()
            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")
            return _serialize_booking(booking)

    @app.patch("/api/bookings/{booking_id}/status")
    async def update_booking_status(
        booking_id: str,
        update: BookingStatusUpdate,
        _admin: str = Depends(get_current_admin),
    ):
        with app.state.db.get_session() as session:
            booking = session.query(Booking).filter(Booking.id == booking_id).first()
            if booking is None:
                raise HTTPException(status_code=404, detail="Booking not found")
            booking.status = update.status
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Cannot confirm booking: the slot is already occupied",
                ) from exc
            return {
                "message": "Status updated",
                "id": booking_id,
                "status": update.status,
            }

    @app.get("/api/services")
    async def get_services(_admin: str = Depends(get_current_admin)):
        with app.state.db.get_session() as session:
            return [
                _serialize_service(service) for service in session.query(Service).all()
            ]

    @app.post("/api/services", status_code=status.HTTP_201_CREATED)
    async def create_service(
        service: ServiceCreate,
        _admin: str = Depends(get_current_admin),
    ):
        with app.state.db.get_session() as session:
            new_service = Service(**service.model_dump())
            session.add(new_service)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(
                    status_code=409, detail="Service already exists"
                ) from exc
            return _serialize_service(new_service)

    @app.put("/api/services/{service_id}")
    async def update_service(
        service_id: str,
        update: ServiceUpdate,
        _admin: str = Depends(get_current_admin),
    ):
        with app.state.db.get_session() as session:
            service = session.query(Service).filter(Service.id == service_id).first()
            if service is None:
                raise HTTPException(status_code=404, detail="Service not found")
            for field, value in update.model_dump(exclude_unset=True).items():
                setattr(service, field, value)
            session.commit()
            return _serialize_service(service)

    @app.delete("/api/services/{service_id}")
    async def delete_service(service_id: str, _admin: str = Depends(get_current_admin)):
        with app.state.db.get_session() as session:
            service = session.query(Service).filter(Service.id == service_id).first()
            if service is None:
                raise HTTPException(status_code=404, detail="Service not found")
            related_bookings = (
                session.query(Booking).filter(Booking.service_id == service_id).count()
            )
            if related_bookings:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete service used by {related_bookings} bookings",
                )
            session.delete(service)
            session.commit()
            return {"message": "Service deleted", "id": service_id}

    @app.get("/api/work-hours")
    async def get_work_hours(_admin: str = Depends(get_current_admin)):
        with app.state.db.get_session() as session:
            hours = session.query(WorkHours).order_by(WorkHours.id).all()
            return [
                {
                    "day_name": day.day_name,
                    "start_time": day.start_time,
                    "end_time": day.end_time,
                    "is_active": day.is_active,
                }
                for day in hours
            ]

    @app.put("/api/work-hours/{day_name}")
    async def update_work_hours(
        day_name: str,
        update: WorkHoursUpdate,
        _admin: str = Depends(get_current_admin),
    ):
        if day_name not in VALID_DAYS:
            raise HTTPException(status_code=400, detail="Invalid day name")
        if update.is_active and update.start_time >= update.end_time:
            raise HTTPException(
                status_code=422, detail="end_time must be after start_time"
            )

        with app.state.db.get_session() as session:
            work_day = (
                session.query(WorkHours).filter(WorkHours.day_name == day_name).first()
            )
            if work_day is None:
                work_day = WorkHours(day_name=day_name)
                session.add(work_day)
            work_day.start_time = update.start_time
            work_day.end_time = update.end_time
            work_day.is_active = update.is_active
            session.commit()
            return {
                "day_name": work_day.day_name,
                "start_time": work_day.start_time,
                "end_time": work_day.end_time,
                "is_active": work_day.is_active,
            }

    @app.get("/api/stats")
    async def get_stats(_admin: str = Depends(get_current_admin)):
        today = datetime.now().date()
        today_text = today.isoformat()
        week_end_text = (today + timedelta(days=7)).isoformat()

        with app.state.db.get_session() as session:
            total_bookings = (
                session.query(Booking).filter(Booking.status == "confirmed").count()
            )
            today_bookings = (
                session.query(Booking)
                .filter(Booking.date == today_text, Booking.status == "confirmed")
                .count()
            )
            week_bookings = (
                session.query(Booking)
                .filter(
                    Booking.date >= today_text,
                    Booking.date <= week_end_text,
                    Booking.status == "confirmed",
                )
                .count()
            )
            cancelled_bookings = (
                session.query(Booking).filter(Booking.status == "cancelled").count()
            )
            services_count = session.query(Service).count()

            booking_count = func.count(Booking.id)
            popular_services = (
                session.query(
                    Booking.service_id,
                    Service.name,
                    booking_count.label("booking_count"),
                )
                .join(Service, Service.id == Booking.service_id)
                .filter(Booking.status == "confirmed")
                .group_by(Booking.service_id, Service.name)
                .order_by(booking_count.desc())
                .limit(5)
                .all()
            )

            return {
                "total_bookings": total_bookings,
                "today_bookings": today_bookings,
                "week_bookings": week_bookings,
                "cancelled_bookings": cancelled_bookings,
                "services_count": services_count,
                "popular_services": [
                    {
                        "service_id": service_id,
                        "service_name": service_name,
                        "count": count,
                    }
                    for service_id, service_name, count in popular_services
                ],
            }

    return app
