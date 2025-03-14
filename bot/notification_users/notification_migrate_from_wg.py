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
# async def send_initial_update_notification(chat_id: int, bot: Bot, errors: dict):
#     """
#     Отправляет уведомление для одного пользователя о новом меню.
#     Если сообщение не отправлено, ошибка записывается в JSON и добавляется в отчёт.
#     """
#     try:
#         # Подключаемся к базе данных
#         async with aiosqlite.connect(db_path) as db:
#             # Проверяем, было ли уведомление отправлено
#             async with db.execute(
#                 "SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)
#             ) as cursor:
#                 row = await cursor.fetchone()
#
#             # Обрабатываем JSON из базы данных
#             if row:
#                 try:
#                     notification_data = json.loads(row[0]) if row[0] else {}
#                 except json.JSONDecodeError:
#                     logger.warning(f"Некорректные данные JSON для пользователя {chat_id}, сбрасываем на пустой объект.")
#                     notification_data = {}
#
#                 # Проверяем наличие уведомления "update_menu"
#                 if "update_menu" in notification_data:
#                     logger.info(f"Пользователь {chat_id} уже уведомлён. Пропускаем.")
#                     return
#             else:
#                 notification_data = {}
#
#             # Текст уведомления
#             text = (
#                 "Привет! 🐧\n"
#                 "🚀 Мы обновили меню для вашего удобства.\n\n"
#                 "Если что-то не работает или появились вопросы, обращайтесь: @pingi_help.\n"
#                 "💡 Мы на связи, чтобы решить любые проблемы!"
#             )
#
#             # Отправляем сообщение с reply-клавиатурой
#             await bot.send_message(
#                 chat_id=chat_id,
#                 text=text,
#                 reply_markup=reply_keyboard_main_menu,
#             )
#
#             # Логируем это уведомление
#             await log_notification(chat_id, "update_menu", "sent")
#             logger.info(f"Уведомление отправлено пользователю {chat_id}")
#
#     except Exception as e:
#         # Обработка ошибок
#         error_message = str(e)
#         logger.error(f"Ошибка при отправке уведомления пользователю {chat_id}: {error_message}")
#
#         # Сохраняем ошибку в notification_data
#         try:
#             async with aiosqlite.connect(db_path) as db:
#                 async with db.execute(
#                     "SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)
#                 ) as cursor:
#                     row = await cursor.fetchone()
#
#                 if row:
#                     try:
#                         notification_data = json.loads(row[0]) if row[0] else {}
#                     except json.JSONDecodeError:
#                         notification_data = {}
#
#                 # Обновляем статус ошибки в JSON
#                 notification_data["update_menu"] = {
#                     "status": "error",
#                     "error": error_message,
#                     "attempted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 }
#
#                 # Обновляем или создаём запись в базе
#                 if row:
#                     await db.execute(
#                         "UPDATE notifications SET notification_data = ? WHERE chat_id = ?",
#                         (json.dumps(notification_data), chat_id),
#                     )
#                 else:
#                     await db.execute(
#                         "INSERT INTO notifications (chat_id, notification_data) VALUES (?, ?)",
#                         (chat_id, json.dumps(notification_data)),
#                     )
#
#                 await db.commit()
#
#         except Exception as db_error:
#             logger.error(f"Ошибка при записи ошибки для пользователя {chat_id}: {db_error}")
#
#         # Добавляем в отчёт для администратора
#         errors[chat_id] = error_message
#
#
#
# # Второе уведомление с inline-кнопками
# async def send_choice_notification(chat_id: int, bot: Bot):
#     """
#     Отправляет второе уведомление с inline-кнопками для выбора действия.
#     """
#     try:
#         # Текст уведомления с выбором действия
#         choice_text = (
#             f"🚨 Улучшения, которые вы ждали!\n\n"
#             f"Мы полностью уходим от *WireGuard*, так как он работает нестабильно, и провайдеры активно блокируют подключение.\n\n"
#             f"📲 Вам нужно добавить ключ *VLESS* и установить новое приложение для подключения. Вам будет доступен 🎁 *пробный период 7 дней*.\n\n"
#         )
#
#         # Создаем inline-кнопки
#         choice_keyboard = InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")],
#                 [InlineKeyboardButton(text="⚠️ Остаться на WireGuard", callback_data="stay_on_wg")]
#             ]
#         )
#
#         # Отправляем сообщение с inline-кнопками
#         await bot.send_message(chat_id=chat_id, text=choice_text, reply_markup=choice_keyboard, parse_mode="Markdown")
#         logger.info(f"Уведомление с выбором отправлено пользователю {chat_id}")
#
#     except Exception as e:
#         logger.error(f"Ошибка при отправке уведомления с выбором: {e}")

# Функция для записи нового уведомления в JSON-структуру
async def log_notification(chat_id: int, notification_type: str, status: str = "sent"):
    """
    Логирует отправку уведомления в JSON-структуру таблицы notifications.
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            # Логируем начало работы с пользователем
            #logger.info(f"Начинаем обработку уведомления для пользователя {chat_id}. Тип: {notification_type}, Статус: {status}")

            # Получаем текущие данные для chat_id
            async with db.execute(
                "SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)
            ) as cursor:
                result = await cursor.fetchone()
                #logger.info(f"Результат запроса из базы для {chat_id}: {result}")

            # Обрабатываем JSON из базы данных
            if result:
                try:
                    notification_data = json.loads(result[0]) if result[0] else {}
                    #logger.info(f"Успешно загружен JSON для пользователя {chat_id}: {notification_data}")
                except json.JSONDecodeError:
                    logger.warning(f"Некорректные данные JSON для пользователя {chat_id}. Заменяем на пустой объект.")
                    notification_data = {}
            else:
                notification_data = {}
                #logger.info(f"Для пользователя {chat_id} записи не найдено. Инициализируем новый JSON.")

            # Обновляем JSON с новым уведомлением
            notification_data[notification_type] = {
                "status": status,
                "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            #logger.info(f"Обновлён JSON для пользователя {chat_id}: {notification_data}")

            # Записываем обновленное значение JSON обратно в базу
            if result:
                await db.execute(
                    "UPDATE notifications SET notification_data = ? WHERE chat_id = ?",
                    (json.dumps(notification_data), chat_id),
                )
                #logger.info(f"Обновлена запись в базе для пользователя {chat_id}.")
            else:
                await db.execute(
                    "INSERT INTO notifications (chat_id, notification_data) VALUES (?, ?)",
                    (chat_id, json.dumps(notification_data)),
                )
                #logger.info(f"Создана новая запись в базе для пользователя {chat_id}.")

            await db.commit()
            #logger.info(f"Успешно завершена обработка уведомления для пользователя {chat_id}.")

    except Exception as e:
        logger.error(f"Ошибка при логировании уведомления для пользователя {chat_id}: {e}")


# async def increment_stay_on_wg_click(chat_id: int):
#     """Функция увеличивает счетчик нажатий на 'Остаться на WireGuard' для пользователя."""
#     async with aiosqlite.connect(db_path) as db:
#         async with db.execute("SELECT notification_data FROM notifications WHERE chat_id = ?", (chat_id,)) as cursor:
#             result = await cursor.fetchone()
#             notification_data = json.loads(result[0]) if result else {}
#
#         # Проверяем, было ли ранее зафиксировано нажатие
#         if notification_data.get("stay_on_wg_clicked", {}).get("status") == "clicked":
#             return  # Если уже нажато, ничего не делаем
#
#         # Обновляем JSON, добавляя отметку о нажатии
#         notification_data["stay_on_wg_clicked"] = {
#             "status": "clicked",
#             "clicked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
#
#         # Записываем обновленное значение JSON обратно в базу
#         if result:
#             await db.execute("UPDATE notifications SET notification_data = ? WHERE chat_id = ?",
#                              (json.dumps(notification_data), chat_id))
#         else:
#             await db.execute("INSERT INTO notifications (chat_id, notification_data) VALUES (?, ?)",
#                              (chat_id, json.dumps(notification_data)))
#
#         await db.commit()

#
# async def get_stay_on_wg_count():
#     """Получает общее количество пользователей, которые нажали 'Остаться на WireGuard'."""
#     async with aiosqlite.connect(db_path) as db:
#         async with db.execute("SELECT notification_data FROM notifications") as cursor:
#             results = await cursor.fetchall()
#             return sum(
#                 1 for row in results if json.loads(row[0]).get("stay_on_wg_clicked", {}).get("status") == "clicked")
#
#
# # Обработчик для inline-кнопок выбора
# @router.callback_query(lambda c: c.data in ["stay_on_wg"])
# async def handle_choice_callback(callback_query: types.CallbackQuery):
#     bot = callback_query.bot
#     chat_id = callback_query.message.chat.id
#
#     # Логируем нажатие кнопки для отслеживания в базе данных
#     await increment_stay_on_wg_click(chat_id)
#     # Пользователь решил остаться на WireGuard
#     warning_text = (
#         f"⚠️ Остаться на WireGuard *не получится*, провайдер *активно* блокирует подключения.\n\n"
#         f"Зачем ждать проблем?\nС *VLESS* у вас будет гарантированная стабильность работы VPN."
#     )
#
#     # Создаем вторую inline-клавиатуру с двумя кнопками
#     second_choice_keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")]
#
#         ]
#     )
#
#     # Отправляем предупреждение и вторую inline-клавиатуру
#     await bot.send_message(chat_id=chat_id, text=warning_text, reply_markup=second_choice_keyboard,
#                            parse_mode="Markdown")
#     await callback_query.answer()
