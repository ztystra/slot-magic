# 🎰 Slot-Magic

[![CI](https://github.com/ztystra/slot-magic/actions/workflows/ci.yml/badge.svg)](https://github.com/ztystra/slot-magic/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4.svg)](https://core.telegram.org/bots/api)

> **Telegram-бот для записи на услуги — салоны красоты, стоматологии, автосервисы.**  
> Клиент выбирает услугу → дату → время → записывается. Бот напоминает.

---

## 🎯 Что это?

Slot-Magic — это готовый к продакшну Telegram-бот для автоматизации записи на услуги. Работает для любой сферы услуг: салоны красоты, стоматологии, автосервисы, клиники, студии.

### Зачем это нужно?

| Без Slot-Magic | С Slot-Magic |
|----------------|--------------|
| Клиент звонит, ждёт ответа | Бот принимает 24/7 мгновенно |
| Менеджер ведёт расписание в Excel | Автоматическое расписание |
| Забывают про напоминания | Бот напоминает за 24ч и за 2ч |
| Теряют клиентов из-за занятости | Клиент видит свободные слоты |

---

## ✨ Возможности

- 📅 **Автоматическая запись** — клиент выбирает услугу, дату, время
- 📋 **Управление расписанием** — настройка рабочих часов и услуг
- ⏰ **Напоминания** — за 24 часа и за 2 часа до записи
- ❌ **Отмена записей** — клиент может отменить через бота
- 💰 **Цены и длительность** — каждая услуга с ценой и временем
- 📊 **Админка** — просмотр всех записей (для владельца)
- 🔄 **Автоматическое обновление** — слоты обновляются в реальном времени

---

## 🚀 Быстрый старт

### 1. Клонируйте

```bash
git clone https://github.com/ztystra/slot-magic.git
cd slot-magic
```

### 2. Установите зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройте

```bash
cp .env.example .env
```

Отредактируйте `.env` — вставьте токен бота:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 4. Запустите

```bash
python bot.py
```

---

## 📖 Как пользоваться

### Клиент

1. Нажимает «📅 Записаться»
2. Выбирает услугу из списка
3. Выбирает дату (ближайшие 7 дней)
4. Выбирает свободное время
5. Указывает имя и телефон
6. Получает подтверждение

### Напоминания

- За 24 часа: «Завтра у вас запись на стрижку в 14:00»
- За 2 часа: «Скоро у вас запись на стрижку в 14:00»

### Отмена

1. Нажимает «📋 Мои записи»
2. Выбирает запись
3. Нажимает «❌ Отменить»

---

## 🏗 Архитектура

```
slot-magic/
├── bot.py              # Telegram-бот (обработчики команд)
├── slot_manager.py     # Менеджер слотов и записей
├── data/               # Данные (создаётся автоматически)
│   ├── services.json   # Услуги
│   ├── bookings.json   # Записи
│   └── work_hours.json # Рабочие часы
├── requirements.txt    # Зависимости
├── .env.example        # Шаблон конфигурации
├── .github/            # CI/CD и шаблоны
├── CONTRIBUTING.md     # Гайд для контрибьюторов
├── SECURITY.md         # Политика безопасности
├── CHANGELOG.md        # История изменений
└── README.md           # Эта документация
```

---

## 🔧 Конфигурация

### Услуги

Услуги настраиваются в `data/services.json`:

```json
[
  {
    "id": "haircut",
    "name": "Стрижка",
    "duration_minutes": 30,
    "price": 800,
    "description": "Мужская/женская стрижка"
  }
]
```

### Рабочие часы

Рабочие часы настраиваются в `data/work_hours.json`:

```json
{
  "monday": {"start": "09:00", "end": "19:00", "active": true},
  "sunday": {"start": "00:00", "end": "00:00", "active": false}
}
```

---

## 💰 Стоимость

| Компонент | Стоимость |
|-----------|-----------|
| Telegram Bot | Бесплатно |
| Хостинг | $5/мес (VPS) |
| Домен | ~500₽/год (опционально) |

**Итого:** ~300₽/мес для работы бота.

---

## 🤝 Контрибьюция

Смотри [CONTRIBUTING.md](CONTRIBUTING.md) для подробностей.

---

## 📝 Лицензия

[MIT License](LICENSE) — используйте как угодно.

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ztystra/slot-magic&type=Date)](https://star-history.com/#ztystra/slot-magic&Date)

---

**Сделано с 💜 [Меру](https://github.com/ztystra)**
