import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from bot.handlers.admin import send_admin_log
from aiogram import Bot
import aiosqlite
from aiogram.exceptions import TelegramForbiddenError
from pytz import timezone

from bot.keyboards.inline import create_feedback_keyboard, account_info_keyboard, subscribe_keyboard, \
    create_payment_button
from bot.utils.subscription_check import check_subscription_channel
from data.text_messages import attention_message

# Настройки

TRIAL_PERIOD_DAYS = 15  # Продолжительность пробного периода
DB_PATH = Path(os.getenv('database_path_local'))  # Путь к базе данных

async def check_db(bot: Bot):
    """
    Основная функция проверки базы данных, обновляющая количество дней с момента регистрации,
    статус подписки и проверяющая подписку на канал.
    """
    try:
        print("Запуск проверки базы данных.")

        users = await get_users_from_db()  # Получаем всех пользователей
        async with aiosqlite.connect(DB_PATH) as db:
            for user in users:
                chat_id, username, registration_date = user


                #расскоментировать при запуске
                await check_everyday_subscription(chat_id, username, bot)

                # Вычисление количества дней с момента регистрации
                days_since_registration = calculate_days_since_registration(registration_date)
                await update_user_days_in_db(chat_id, days_since_registration, db)

                # if status == "activ":
                #     days_since_registration = calculate_days_since_registration(registration_date)
                #     await update_user_days_in_db(chat_id, days_since_registration, db)
                #


                # Обновление статуса подписки
                await update_subscription_status(chat_id, days_since_registration, db, bot)
        # print(f"Проверка завершена. Статус {notificated_user} пользователей был обновлен на 'waiting_pending'.")
        # await send_admin_log(bot,
        #                      f"Статус {notificated_user} пользователей был обновлен на 'waiting_pending'. Сообщения отправлены.")
    except Exception as e:
        logging.error(f"Ошибка при выполнении проверки базы данных: {e}")
async def get_users_from_db():
    """Получение всех пользователей из базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id, user_name, registration_date FROM users")
        users = await cursor.fetchall()
        return users


def calculate_days_since_registration(registration_date):
    """Вычисление количества дней с даты регистрации"""
    try:
        reg_date = parse_registration_date(registration_date)
        current_date = datetime.now()
        return (current_date - reg_date).days
    except ValueError as e:
        logging.error(f"Ошибка при парсинге даты регистрации: {e}")
        return -1


async def update_user_days_in_db(chat_id, days, db):
    """Обновление количества дней с момента регистрации"""
    try:
        await db.execute("UPDATE users SET days_since_registration = ? WHERE chat_id = ?", (days, chat_id))
        await db.commit()
        logging.info(f"Количество дней с момента регистрации обновлено для пользователя {chat_id}: {days} дней.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении данных пользователя {chat_id}: {e}")





async def update_subscription_status(chat_id, days_since_registration, db, bot):
    """
    Обновляет статус подписки пользователя на бота в зависимости от количества дней с момента регистрации.
    """
    try:
        if days_since_registration > 14:
            # Получаем текущий статус и значение is_notification
            logging.info(
                f"Проверяем статус подписки для пользователя {chat_id} с {days_since_registration} дней регистрации.")

            cursor = await db.execute('''
                SELECT subscription_status, is_notification
                FROM users
                WHERE chat_id = ?
            ''', (chat_id,))
            result = await cursor.fetchone()

            if result:
                current_status, is_notification = result
                logging.info(
                    f"Получен статус подписки {current_status} и статус уведомления {is_notification} для пользователя {chat_id}.")

                # Если статус ещё не "waiting_pending", обновляем его
                if current_status != 'waiting_pending':
                    logging.info(f"Обновляем статус подписки пользователя {chat_id} на 'waiting_pending'.")
                    await db.execute('''
                        UPDATE users
                        SET subscription_status = 'waiting_pending'
                        WHERE chat_id = ?
                    ''', (chat_id,))
                    await db.commit()
                    logging.info(f"Статус пользователя {chat_id} обновлен на 'waiting_pending'.")

                # Проверяем is_notification, чтобы отправить уведомление только один раз
                if is_notification == 0 or 1 :
                    try:
                        logging.info(f"Отправляем уведомление пользователю {chat_id}.")
                        # Отправляем сообщение пользователю
                        warning_message = (
                            "Ваш пробный период истек. \n"
                            "Оплата доступна, вам необходимо оплатить чтобы продолжить пользоваться VPN.\n\n "
                        )
                        await db.execute('''                           UPDATE users
                                                                       SET is_notification = 1
                                                                       WHERE chat_id = ?
                                                                   ''', (chat_id,))
                        await bot.send_message(chat_id, warning_message, reply_markup=create_payment_button(chat_id))#, reply_markup=account_info_keyboard())

                        await db.commit()
                        logging.info(f"Уведомление отправлено пользователю {chat_id}.")


                        # Логируем отправку уведомления администратору
                        await send_admin_log(bot,
                                             f"Уведомление отправлено пользователю {chat_id} о завершении пробного периода.")

                        # Обновляем поле is_notification на True (1)
                        logging.info(f"Обновляем поле is_notification для пользователя {chat_id}.")
                        await db.execute('''
                            UPDATE users
                            SET is_notification = 2
                            WHERE chat_id = ?
                        ''', (chat_id,))
                        await db.commit()
                        logging.info(f"Поле is_notification для пользователя {chat_id} обновлено.")

                    except TelegramForbiddenError:
                        logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")

                    except Exception as e:
                        logging.error(f"Ошибка при отправке уведомления пользователю {chat_id}: {e}")
            else:
                logging.error(f"Не удалось найти информацию о подписке для chat_id {chat_id}.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении статуса подписки для пользователя {chat_id}: {e}")

async def check_everyday_subscription(chat_id: int, username: str, bot: Bot) -> bool:
    """
    Проверяет подписку пользователя на канал и отправляет уведомления в случае отписки.
    Продолжает выполнение даже в случае ошибок, таких как блокировка бота или некорректный chat_id.

    :param chat_id: Идентификатор чата пользователя.
    :param username: Имя пользователя.
    :param bot: Экземпляр бота для отправки сообщений.
    :return: Возвращает True, если пользователь подписан, иначе False.
    """
    try:


        # Проверка подписки на канал
        is_subscribed = await check_subscription_channel(chat_id, bot)

        if not is_subscribed:
            # Сообщение пользователю о необходимости подписки
            warning_message = (
                "Вы отписались от нашего канала. Пожалуйста, подпишитесь обратно, чтобы продолжить пользоваться VPN."
            )
            try:
                await bot.send_message(chat_id, warning_message, reply_markup=subscribe_keyboard())
                logging.info(f"Отправлено уведомление пользователю с chat_id: {chat_id} о необходимости подписки.")
            except Exception as e:
                if 'Forbidden: bot was blocked by the user' in str(e):
                    logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
                else:
                    logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

            # Сообщение администратору о том, что пользователь отписался
            await send_admin_log(bot, f"Пользователь с chat_id {chat_id} (username: @{username}) отписался от канала.")
            logging.info(f"Отправлено уведомление администратору о том, что пользователь с chat_id: {chat_id} отписался от канала.")

            return False

        logging.info(f"Пользователь с chat_id {chat_id} подписан на канал.")
        return True

    except Exception as e:
        if 'PARTICIPANT_ID_INVALID' in str(e):
            logging.error(f"Ошибка PARTICIPANT_ID_INVALID для chat_id {chat_id}: пользователь не найден в канале.")
            try:
                warning_message = (
                    "Мы не можем проверить вашу подписку на канал. Пожалуйста, убедитесь, что вы подписаны."
                )
                await bot.send_message(chat_id, warning_message)
            except Exception as send_error:
                if 'Forbidden: bot was blocked by the user' in str(send_error):
                    logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
                else:
                    logging.error(f"Ошибка при отправке уведомления для chat_id {chat_id}: {send_error}")

            await send_admin_log(bot, f"Пользователь с chat_id {chat_id} не найден в канале. PARTICIPANT_ID_INVALID.")
            return False

        if 'Forbidden: bot was blocked by the user' in str(e):
            logging.error(f"Бот заблокирован пользователем {chat_id}, проверка подписки не выполнена.")
            return False

        if 'Bad Request: chat not found' in str(e):
            logging.error(f"Ошибка Bad Request: чат с chat_id {chat_id} не найден.")
            return False

        # Логирование других ошибок
        logging.error(f"Ошибка при проверке подписки для chat_id {chat_id}: {e}")
        return False


def parse_registration_date(date_str):
    """
    Функция для обработки даты регистрации в разных форматах.
    """
    formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]  # Форматы с миллисекундами и без

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue  # Пробуем следующий формат, если текущий не подходит

    raise ValueError(f"Не удалось распарсить дату: {date_str}")



# # Функция для проверки статуса пользователя и отправки сообщения, если статус "free"
# async def check_and_notify_free_user(conn, bot: Bot, chat_id: int, message: str):
#     """
#     Проверяет текущий статус пользователя, отправляет сообщение, если статус 'free',
#     и обновляет его на 'waiting_pending'.
#
#     :param conn: Подключение к базе данных
#     :param bot: Объект бота для отправки сообщения
#     :param chat_id: Идентификатор пользователя (chat_id)
#     :param message: Сообщение, которое будет отправлено пользователю
#     """
#     try:
#         # Получаем текущий статус пользователя
#         cursor = await conn.execute('''
#             SELECT subscription_status
#             FROM users
#             WHERE chat_id = ?
#         ''', (chat_id,))
#         row = await cursor.fetchone()
#
#         # Проверяем, найден ли пользователь
#         if row:
#             current_status = row[0]
#
#             # Если статус 'free', отправляем сообщение и обновляем статус на 'waiting_pending'
#             if current_status == 'free':
#                 #await bot.send_message(456717505, f"в чат {chat_id} будет отправлено {message}",reply_markup=create_feedback_keyboard())
#                 print(f"Сообщение отправлено пользователю с chat_id {chat_id} current_status == 'free'")
#
#                 # Обновляем статус на 'waiting_pending'
#                 await conn.execute('''
#                     UPDATE users
#                     SET subscription_status = 'waiting_pending'
#                     WHERE chat_id = ?
#                 ''', (chat_id,))
#                 await conn.commit()
#                 print(f"Статус пользователя с chat_id {chat_id} обновлен на 'waiting_pending'")
#             else:
#                 print(f"Пользователь с chat_id {chat_id} имеет статус: {current_status}. Сообщение не отправлено.")
#         else:
#             print(f"Пользователь с chat_id {chat_id} не найден.")
#
#     except Exception as e:
#         print(f"Ошибка при обработке пользователя с chat_id {chat_id}: {e}")
#
#
# # Основная функция для обработки всех пользователей с пробным периодом
# async def process_free_users(bot: Bot, message: str):
#     conn = await aiosqlite.connect(DB_PATH)
#     try:
#         # Получаем пользователей, у которых статус 'free'
#         cursor = await conn.execute('''
#             SELECT chat_id
#             FROM users
#             WHERE subscription_status = 'free'
#         ''')
#         free_users = await cursor.fetchall()
#
#         print(f"Пользователи со статусом 'free': {free_users}")
#
#         # Отправляем сообщения и обновляем статусы для всех пользователей со статусом 'free'
#         for user in free_users:
#             chat_id = user[0]
#
#             # Проверка и отправка сообщения пользователю с обновлением статуса
#             await check_and_notify_free_user(conn, bot, chat_id, message)
#
#         # После обработки всех пользователей, проверим еще раз, что статусы обновлены корректно
#         updated_cursor = await conn.execute('''
#             SELECT chat_id, subscription_status
#             FROM users
#             WHERE subscription_status = 'waiting_pending'
#         ''')
#         updated_users = await updated_cursor.fetchall()
#
#         print(f"Пользователи с обновленным статусом 'waiting_pending': {updated_users}")
#
#     finally:
#         await conn.close()
#
#
# # Пример использования
# async def notify_users_with_free_status(bot: Bot):
#     await process_free_users(bot, attention_message)
