import json
from datetime import datetime

import aiosqlite
from aiogram import types, Bot, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging

from bot.keyboards.inline import main_menu_inline_keyboard
from bot.handlers.all_menu.main_menu import show_main_menu
from bot.keyboards.reply import reply_keyboard_main_menu
from bot.payments2.payments_handler_redis import db_path

logger = logging.getLogger(__name__)
router = Router()
# Основное уведомление с reply-клавиатурой
async def send_initial_update_notification(chat_id: int, bot: Bot):
    """
    Отправляет первое уведомление об обновлении с reply-клавиатурой.
    """
    try:
        # Формируем текст для основного уведомления
        text = (
            "🚨 *У нас обновление!* 🚨\n\n"
            "Теперь доступен новый протокол *VLESS* с улучшенными характеристиками скорости и защиты.\n\n"
            "⚙️ *Высокая скорость*\n"
            "🛡️ *Защита и анонимность*\n"
            "📈 *Стабильность*\n"
            "📲 Переходите на новый протокол для максимального удобства и надежности!"
        )

        # Отправляем сообщение с reply-клавиатурой
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_keyboard_main_menu, parse_mode="Markdown")

        # Логируем это уведомление
        await log_notification(chat_id, "transition_to_vless", "sent")
        logger.info(f"Основное уведомление об обновлении отправлено пользователю {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке основного уведомления: {e}")


# Второе уведомление с inline-кнопками
async def send_choice_notification(chat_id: int, bot: Bot):
    """
    Отправляет второе уведомление с inline-кнопками для выбора действия.
    """
    try:
        # Текст уведомления с выбором действия
        choice_text = (
            f"🚨 Улучшения, которые вы ждали!\n\n"
            f"Мы полностью уходим от *WireGuard*, так как он работает нестабильно, и провайдеры активно блокируют подключение.\n\n"
            f"📲 Вам нужно добавить ключ *VLESS* и установить новое приложение для подключения. Вам будет доступен 🎁 *пробный период 7 дней*.\n\n"
        )

        # Создаем inline-кнопки
        choice_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")],
                [InlineKeyboardButton(text="⚠️ Остаться на WireGuard", callback_data="stay_on_wg")]
            ]
        )

        # Отправляем сообщение с inline-кнопками
        await bot.send_message(chat_id=chat_id, text=choice_text, reply_markup=choice_keyboard, parse_mode="Markdown")
        logger.info(f"Уведомление с выбором отправлено пользователю {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления с выбором: {e}")


# Функция для записи нового уведомления в JSON-структуру
async def log_notification(chat_id: int, notification_type: str, status: str = "sent"):
    async with aiosqlite.connect(db_path) as db:
        # Получаем текущие данные для chat_id
        async with db.execute("SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)) as cursor:
            result = await cursor.fetchone()
            notification_data = json.loads(result[0]) if result else {}

        # Обновляем JSON с новым уведомлением
        notification_data[notification_type] = {
            "status": status,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Записываем обновленное значение JSON обратно в базу
        if result:
            await db.execute("UPDATE notifications SET notification_data = ? WHERE chat_id = ?",
                             (json.dumps(notification_data), chat_id))
        else:
            await db.execute("INSERT INTO notifications (chat_id, notification_data) VALUES (?, ?)",
                             (chat_id, json.dumps(notification_data)))

        await db.commit()

async def increment_stay_on_wg_click(chat_id: int):
    """Функция увеличивает счетчик нажатий на 'Остаться на WireGuard' для пользователя."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)) as cursor:
            result = await cursor.fetchone()
            notification_data = json.loads(result[0]) if result else {}

        # Проверяем, было ли ранее зафиксировано нажатие
        if notification_data.get("stay_on_wg_clicked", {}).get("status") == "clicked":
            return  # Если уже нажато, ничего не делаем

        # Обновляем JSON, добавляя отметку о нажатии
        notification_data["stay_on_wg_clicked"] = {
            "status": "clicked",
            "clicked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Записываем обновленное значение JSON обратно в базу
        if result:
            await db.execute("UPDATE notifications SET notification_data = ? WHERE chat_id = ?",
                             (json.dumps(notification_data), chat_id))
        else:
            await db.execute("INSERT INTO notifications (chat_id, notification_data) VALUES (?, ?)",
                             (chat_id, json.dumps(notification_data)))

        await db.commit()
async def get_stay_on_wg_count():
    """Получает общее количество пользователей, которые нажали 'Остаться на WireGuard'."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT notification_data FROM notifications") as cursor:
            results = await cursor.fetchall()
            return sum(1 for row in results if json.loads(row[0]).get("stay_on_wg_clicked", {}).get("status") == "clicked")
# Обработчик для inline-кнопок выбора
@router.callback_query(lambda c: c.data in ["stay_on_wg"])
async def handle_choice_callback(callback_query: types.CallbackQuery):
    bot = callback_query.bot
    chat_id = callback_query.message.chat.id

    # Логируем нажатие кнопки для отслеживания в базе данных
    await increment_stay_on_wg_click(chat_id)
    # Пользователь решил остаться на WireGuard
    warning_text = (
        f"⚠️ Остаться на WireGuard *не получится*, провайдер *активно* блокирует подключения.\n\n"
        f"Зачем ждать проблем?\nС *VLESS* у вас будет гарантированная стабильность работы VPN."
    )

    # Создаем вторую inline-клавиатуру с двумя кнопками
    second_choice_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")]

        ]
    )

    # Отправляем предупреждение и вторую inline-клавиатуру
    await bot.send_message(chat_id=chat_id, text=warning_text, reply_markup=second_choice_keyboard, parse_mode="Markdown")
    await callback_query.answer()
