"""
Slot-Magic Bot — Telegram бот для записи на услуги.
Работает для салонов красоты, стоматологий, автосервисов.
"""

import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from slot_manager import SlotManager

# Load env
load_dotenv()

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Slot Manager
manager = SlotManager()

# User states
user_states = {}  # user_id -> current state


def get_main_keyboard():
    """Главное меню."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📅 Записаться"), KeyboardButton("📋 Мои записи")],
            [KeyboardButton("❓ Помощь")],
        ],
        resize_keyboard=True,
    )


def get_services_keyboard():
    """Клавиатура услуг."""
    services = manager.get_services()
    buttons = []
    for s in services:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{s['name']} — {s['price']}₽ ({s['duration_minutes']} мин)",
                    callback_data=f"service:{s['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(buttons)


def get_dates_keyboard(service_id: str):
    """Клавиатура дат (ближайшие 7 дней)."""
    buttons = []
    today = datetime.now()

    for i in range(1, 8):
        date = today + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        date_display = date.strftime("%d.%m (%a)")

        # Проверяем есть ли свободные слоты
        slots = manager.get_available_slots(date_str, service_id)
        if slots:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{date_display} — {len(slots)} свободных",
                        callback_data=f"date:{service_id}:{date_str}",
                    )
                ]
            )

    if not buttons:
        return None

    return InlineKeyboardMarkup(buttons)


def get_time_keyboard(service_id: str, date: str):
    """Клавиатура времени."""
    slots = manager.get_available_slots(date, service_id)
    if not slots:
        return None

    buttons = []
    for i in range(0, len(slots), 2):
        row = []
        for j in range(2):
            if i + j < len(slots):
                row.append(
                    InlineKeyboardButton(
                        slots[i + j],
                        callback_data=f"time:{service_id}:{date}:{slots[i + j]}",
                    )
                )
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start."""
    await update.message.reply_text(
        "✨ **Добро пожаловать в Slot-Magic!**\n\n" "Выберите действие из меню 👇",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help."""
    await update.message.reply_text(
        "**Как записаться:**\n\n"
        "1️⃣ Нажмите «📅 Записаться»\n"
        "2️⃣ Выберите услугу\n"
        "3️⃣ Выберите дату\n"
        "4️⃣ Выберите время\n"
        "5️⃣ Укажите имя и телефон\n\n"
        "**Отмена записи:**\n"
        "Нажмите «📋 Мои записи» и выберите запись для отмены.\n\n"
        "**Напоминания:**\n"
        "Бот напомнит о записи за 24 часа и за 2 часа.",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений."""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "📅 Записаться":
        await update.message.reply_text(
            "Выберите услугу:", reply_markup=get_services_keyboard()
        )
        return

    if text == "📋 Мои записи":
        bookings = manager.get_client_bookings(user_id)
        if not bookings:
            await update.message.reply_text("У вас нет активных записей.")
            return

        for b in bookings:
            service = manager.get_service(b["service_id"])
            service_name = service["name"] if service else b["service_id"]

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "❌ Отменить", callback_data=f"cancel:{b['id']}"
                        )
                    ]
                ]
            )

            await update.message.reply_text(
                f"📋 **Запись:**\n\n"
                f"**Услуга:** {service_name}\n"
                f"**Дата:** {b['date']}\n"
                f"**Время:** {b['time']}\n"
                f"**Статус:** {b['status']}",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        return

    if text == "❓ Помощь":
        await help_cmd(update, context)
        return

    # State machine для ввода данных
    state = user_states.get(user_id, {})

    if state.get("step") == "wait_name":
        user_states[user_id] = {
            "step": "wait_phone",
            "service_id": state["service_id"],
            "date": state["date"],
            "time": state["time"],
            "name": text,
        }
        await update.message.reply_text("Отлично! Теперь укажите ваш телефон:")
        return

    if state.get("step") == "wait_phone":
        # Создаём запись
        booking = manager.create_booking(
            service_id=state["service_id"],
            date=state["date"],
            time=state["time"],
            client_name=state["name"],
            client_phone=text,
            client_telegram_id=user_id,
        )

        # Очищаем состояние
        user_states.pop(user_id, None)

        if booking:
            service = manager.get_service(state["service_id"])
            await update.message.reply_text(
                f"✅ **Запись создана!**\n\n"
                f"**Услуга:** {service['name']}\n"
                f"**Дата:** {state['date']}\n"
                f"**Время:** {state['time']}\n"
                f"**Имя:** {state['name']}\n"
                f"**Телефон:** {text}\n\n"
                f"Бот напомнит о записи за 24 часа и за 2 часа.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании записи. Возможно слот уже занят.",
                reply_markup=get_main_keyboard(),
            )
        return

    # По умолчанию
    await update.message.reply_text(
        "Используйте кнопки меню для навигации.", reply_markup=get_main_keyboard()
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback кнопок."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # Выбор услуги
    if data.startswith("service:"):
        service_id = data.split(":")[1]
        service = manager.get_service(service_id)

        keyboard = get_dates_keyboard(service_id)
        if not keyboard:
            await query.edit_message_text(
                f"❌ Нет свободных слотов на ближайшие 7 дней для «{service['name']}»."
            )
            return

        await query.edit_message_text(
            f"Вы выбрали: **{service['name']}** — {service['price']}₽\n\n"
            f"Выберите дату:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # Выбор даты
    if data.startswith("date:"):
        parts = data.split(":")
        service_id = parts[1]
        date = parts[2]

        keyboard = get_time_keyboard(service_id, date)
        if not keyboard:
            await query.edit_message_text("❌ Нет свободных слотов на эту дату.")
            return

        date_display = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y (%A)")
        await query.edit_message_text(
            f"📅 **{date_display}**\n\nВыберите время:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    # Выбор времени
    if data.startswith("time:"):
        parts = data.split(":")
        service_id = parts[1]
        date = parts[2]
        time = parts[3]

        # Сохраняем состояние
        user_states[user_id] = {
            "step": "wait_name",
            "service_id": service_id,
            "date": date,
            "time": time,
        }

        service = manager.get_service(service_id)
        await query.edit_message_text(
            f"✅ **{service['name']}**\n"
            f"📅 {date} в {time}\n\n"
            f"Укажите ваше имя:",
            parse_mode="Markdown",
        )
        return

    # Отмена записи
    if data.startswith("cancel:"):
        booking_id = data.split(":")[1]

        if manager.cancel_booking(booking_id):
            await query.edit_message_text("✅ Запись отменена.")
        else:
            await query.edit_message_text("❌ Ошибка при отмене записи.")
        return


async def send_reminders(app):
    """Отправить напоминания (вызывается по расписанию)."""
    # Напоминание за 24 часа
    bookings_24h = manager.get_bookings_needing_reminder(24)
    for b in bookings_24h:
        try:
            service = manager.get_service(b["service_id"])
            service_name = service["name"] if service else b["service_id"]

            await app.bot.send_message(
                chat_id=b["client_telegram_id"],
                text=(
                    f"⏰ **Напоминание (через 24 часа)**\n\n"
                    f"Завтра у вас запись:\n"
                    f"**Услуга:** {service_name}\n"
                    f"**Дата:** {b['date']}\n"
                    f"**Время:** {b['time']}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send 24h reminder: {e}")

    # Напоминание за 2 часа
    bookings_2h = manager.get_bookings_needing_reminder(2)
    for b in bookings_2h:
        try:
            service = manager.get_service(b["service_id"])
            service_name = service["name"] if service else b["service_id"]

            await app.bot.send_message(
                chat_id=b["client_telegram_id"],
                text=(
                    f"⏰ **Напоминание (через 2 часа)**\n\n"
                    f"Скоро у вас запись:\n"
                    f"**Услуга:** {service_name}\n"
                    f"**Время:** {b['time']}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send 2h reminder: {e}")


def main():
    """Запуск бота."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return

    app = Application.builder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Reminders (каждые 15 минут)
    app.job_queue.run_repeating(send_reminders, interval=900, first=60)  # 15 минут

    # Run
    print("🎰 Slot-Magic Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
