# 🎰 Slot-Magic

[![CI](https://github.com/ztystra/slot-magic/actions/workflows/ci.yml/badge.svg)](https://github.com/ztystra/slot-magic/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Telegram-бот для онлайн-записи и веб-панель владельца бизнеса. Один экземпляр подходит для салона, стоматологии, автосервиса или частного специалиста.

> **Статус:** рабочий MVP для демонстрации и пилотного запуска. Для высоконагруженного production нужны PostgreSQL, HTTPS/reverse proxy и резервное копирование.

## Возможности

### Для клиента в Telegram

- выбор услуги, даты и свободного времени;
- создание и отмена собственной записи;
- защита от двойной записи на один слот;
- напоминания за 24 часа и 2 часа.

### Для владельца в веб-панели

- JWT-авторизация без встроенных дефолтных паролей;
- статистика по записям и популярным услугам;
- фильтр записей по дате;
- перевод записи в `completed` или `cancelled`;
- создание, изменение и удаление услуг;
- настройка рабочих часов.

Бот и админка работают с одной SQLite-базой через SQLAlchemy. Изменённая в панели услуга сразу доступна в боте.

## Быстрый старт

```bash
git clone https://github.com/ztystra/slot-magic.git
cd slot-magic
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
SQLITE_DB_PATH=slot_magic.db
ADMIN_USERNAME=owner
ADMIN_PASSWORD=use-a-long-random-password
JWT_SECRET=use-at-least-32-random-characters
```

Секрет для JWT можно создать командой:

```bash
openssl rand -hex 32
```

### Запуск бота

```bash
python bot.py
```

### Запуск админки

```bash
uvicorn admin.main:create_app --factory --host 127.0.0.1 --port 8000
```

Откройте [http://127.0.0.1:8000](http://127.0.0.1:8000) и войдите данными `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

## Docker Compose

Оба сервиса используют файл `./data/slot_magic.db`:

```bash
docker compose up --build
```

- Telegram-бот: работает в фоне;
- админка: `http://localhost:8000`.

Не публикуйте порт 8000 напрямую в интернет. Перед внешним запуском поставьте Caddy/Nginx с HTTPS и ограничением частоты запросов к `/api/auth/login`.

## API

После запуска документация доступна по адресу `http://127.0.0.1:8000/docs`.

Основные маршруты:

| Метод | Маршрут | Назначение |
|---|---|---|
| `POST` | `/api/auth/login` | получить JWT |
| `GET` | `/api/bookings` | список записей |
| `PATCH` | `/api/bookings/{id}/status` | изменить статус |
| `GET/POST` | `/api/services` | список/создание услуг |
| `PUT/DELETE` | `/api/services/{id}` | изменение/удаление услуги |
| `GET/PUT` | `/api/work-hours/{day}` | рабочие часы |
| `GET` | `/api/stats` | статистика |
| `GET` | `/api/health` | health check |

Все маршруты кроме login и health требуют `Authorization: Bearer <token>`.

## Тесты и проверки

```bash
pytest tests/ -v
black --check bot.py slot_manager.py database.py admin tests
isort --profile black --check-only bot.py slot_manager.py database.py admin tests
flake8 bot.py slot_manager.py database.py admin tests --max-line-length=100 --ignore=E501,W503
```

Тесты покрывают работу слотов, IDOR-защиту отмены, повторную запись после отмены, миграцию старой схемы, авторизацию и CRUD API админки.

## Архитектура

```text
slot-magic/
├── bot.py                    # Telegram UI
├── slot_manager.py           # бизнес-логика записи
├── database.py               # SQLAlchemy models + migration
├── admin/
│   ├── main.py               # FastAPI + auth + API
│   └── frontend/index.html   # React dashboard без build-step
├── tests/                    # unit/integration tests
├── Dockerfile
└── docker-compose.yml
```

## Ограничения MVP

- SQLite подходит одному филиалу и умеренной нагрузке, но не горизонтальному масштабированию;
- один экземпляр приложения обслуживает одну организацию;
- платежи и мульти-тенантность пока не реализованы;
- React загружается с CDN, поэтому для полностью автономного production-деплоя нужен собранный frontend bundle;
- rate limiting логина должен выполняться reverse proxy или API gateway.

## Лицензия

[MIT](LICENSE)
