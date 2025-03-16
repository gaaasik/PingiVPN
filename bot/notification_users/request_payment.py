# import asyncio
# import logging
# import json
# import os
# from datetime import datetime
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# import aiosqlite
#
# from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
# from bot.notification_users.notification_migrate_from_wg import log_notification
# from models.UserCl import UserCl
#
# # Логгер
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
# # Константы
# DB_PATH = os.getenv('database_path_local')  # Замените на путь к вашей базе данных
# BATCH_SIZE = 50  # Размер батча для отправки
#
#
# # Клавиатура оплаты
# def get_payment_keyboard() -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="💳 Оплатить ключ", callback_data="buy_vpn")],
#             [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
#         ]
#     )
#
#
# # # Основная функция обработки уведомлений
# # async def process_notifications_request_payment(bot):
# #     """
# #     Обработка уведомлений о запросе оплаты:
# #     1. Определяет список пользователей, кому нужно отправить уведомления.
# #     2. Делит список на батчи.
# #     3. Отправляет уведомления пользователям и логирует их статус.
# #     """
# #     await asyncio.sleep(1)
# #     logging.info("Начинаем процесс обработки уведомлений о запросе оплаты.")
# #
# #     users_to_notify, users_skipped = await find_users_for_notification()
# #     # Ограничиваем список до первых 1100 пользователей
# #     users_to_notify = users_to_notify[:500]
# #
# #     logging.info(f"Найдено {len(users_to_notify)} пользователей для уведомлений.")
# #     logging.info(f"Пропущено {len(users_skipped)} пользователей из-за отсутствия данных.")
# #
# #     errors = {}
# #
# #     async def send_batch(batch):
# #         await asyncio.gather(*[send_notification_to_user(bot, chat_id, errors) for chat_id in batch])
# #
# #     for i in range(0, len(users_to_notify), BATCH_SIZE):
# #         batch = users_to_notify[i:i + BATCH_SIZE]
# #         await send_batch(batch)
# #
# #     # Итоговый отчёт
# #     logging.info(f"Процесс завершён. Успешно отправлено: {len(users_to_notify) - len(errors)}.")
# #     logging.info(f"Ошибки при отправке: {len(errors)}. Подробности: {errors}")
#
# from datetime import datetime
# import logging
#
# #
# # async def find_users_for_notification():
# #     """
# #     Ищет пользователей с истёкшим периодом ключа.
# #     Возвращает два списка: кому нужно отправить уведомление и кого пропустить.
# #     """
# #     current_time = datetime.now()
# #     users_to_notify = []
# #     users_skipped = []
# #
# #     # Загружаем всех пользователей из базы
# #     user_ids = await UserCl.get_all_users()  # Получаем список chat_id
# #     for user_id in user_ids:
# #         try:
# #             # Загружаем объект пользователя
# #             us = await UserCl.load_user(user_id)
# #             if not us:
# #                 logging.warning(f"Пользователь с chat_id {user_id} не найден.")
# #                 users_skipped.append(user_id)
# #                 continue
# #
# #             # Проверяем наличие серверов у пользователя
# #             if not us.servers:
# #                 logging.warning(f"У пользователя {us.chat_id} нет серверов.")
# #                 users_skipped.append(us.chat_id)
# #                 continue
# #
# #             # Получаем дату окончания ключа
# #             date_key_off = await us.servers[0].date_key_off.get()
# #
# #             if date_key_off:
# #                 # Если `date_key_off` строка, преобразуем её в объект `datetime`
# #                 if isinstance(date_key_off, str):
# #                     try:
# #                         date_key_off = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
# #                     except ValueError as e:
# #                         logging.error(f"Ошибка преобразования даты у пользователя {us.chat_id}: {e}")
# #                         users_skipped.append(us.chat_id)
# #                         continue
# #
# #                 # Сравниваем дату окончания с текущей датой
# #                 if date_key_off < current_time:
# #                     users_to_notify.append(us.chat_id)
# #                 else:
# #                     users_skipped.append(us.chat_id)
# #             else:
# #                 #logging.warning(f"У пользователя {us.chat_id} отсутствует дата окончания ключа.")
# #                 users_skipped.append(us.chat_id)
# #
# #         except Exception as e:
# #             logging.error(f"Ошибка при обработке пользователя {user_id}: {e}")
# #             users_skipped.append(user_id)
# #     print(len(users_to_notify), "users_skipped = ", len(users_skipped))
# #     return users_to_notify, users_skipped
# #
#
#
#
# # async def send_notification_to_user(bot, chat_id, errors, notification_type="request_payment2"):
# #     """
# #     Отправляет уведомление пользователю и логирует результат через log_notification.
# #     """
# #     try:
# #         # Сообщение
# #         text = (
# #             "⏳ Ваш пробный период завершён!\n\n"
# #             "Чтобы продолжить пользоваться VPN, пожалуйста, оплатите подписку.\n"
# #             "Нажмите на кнопку ниже для оплаты."
# #         )
# #         keyboard = get_payment_keyboard()
# #
# #         # Отправка сообщения
# #
# #         await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")
# #         logging.info(f"Уведомление отправлено пользователю {chat_id}.")
# #
# #         # Логирование успешной отправки
# #         await log_notification(chat_id, notification_type, status="sent")
# #
# #     except Exception as e:
# #         # Логирование ошибки
# #         error_message = f"Ошибка при отправке уведомления: {str(e)}"
# #         logging.error(f"{error_message} для пользователя {chat_id}.")
# #         errors[chat_id] = error_message
# #
# #         # Логируем ошибку в базе
# #         await log_notification(chat_id, notification_type, status="error")
# #
#
