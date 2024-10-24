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
                await check_everyday_subscription_on_channel(chat_id, username, bot)

                # Вычисление количества дней с момента регистрации
                days_since_registration = calculate_days_since_registration(registration_date)
                await update_user_days_in_db(chat_id, days_since_registration, db)

                # if status == "activ":
                #     days_since_registration = calculate_days_since_registration(registration_date)
                #     await update_user_days_in_db(chat_id, days_since_registration, database)
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


async def check_everyday_subscription_on_channel(chat_id: int, username: str, bot: Bot) -> bool:
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
                f"Вы не подписаны на наш канал. \n Подпишитесь, чтобы продолжить пользоваться VPN."
            )
            try:
                #раскомментировать при запуске
                await bot.send_message(chat_id, warning_message, reply_markup=subscribe_keyboard())
                #
                await send_admin_log(bot, f"Пользователь{chat_id} с @{username} не подписан на канал")
                logging.info(f"Отправлено уведомление пользователю с chat_id: {chat_id} о необходимости подписки.")
            except Exception as e:
                await send_admin_log(bot,f"Ошибка при отправке сообщения пользователю {chat_id}: {e}\n {warning_message}")
                if 'Forbidden: bot was blocked by the user' in str(e):
                    logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
                else:
                    logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

            return False
        # else:
        #     await send_admin_log(bot, f"Пользователь{chat_id} с @{username} подписан на канал")

        logging.info(f"Пользователь с chat_id {chat_id} подписан на канал.")
        return True

    except Exception as e:
        if 'PARTICIPANT_ID_INVALID' in str(e):
            logging.error(f"Ошибка PARTICIPANT_ID_INVALID для chat_id {chat_id}: пользователь не найден в канале.")
            try:
                warning_message = (
                    f"Мы не можем проверить вашу подписку на канал. \n Пожалуйста, убедитесь, что вы подписаны."
                )
                await bot.send_message(chat_id, warning_message, reply_markup=subscribe_keyboard())
            except Exception as send_error:

                if 'Forbidden: bot was blocked by the user' in str(send_error):
                    logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
                else:
                    logging.error(f"Ошибка при отправке уведомления для chat_id {chat_id}: {send_error}")

            #await send_admin_log(bot, f"Пользователь с chat_id {chat_id} не найден в канале. PARTICIPANT_ID_INVALID.")
            return False

        if 'Forbidden: bot was blocked by the user' in str(e):
            logging.error(f"Бот заблокирован пользователем {chat_id}, проверка подписки не выполнена.")
            return False

        if 'Bad Request: chat not found' in str(e):
            logging.error(f"Ошибка Bad Request: чат с chat_id {chat_id} не найден.")
            return False

        # Логирование других ошибок
        logging.error(f"Ошибка при проверке подписки для chat_id {chat_id}: {e}")
        await send_admin_log(bot, f"Ошибка при отправке уведомления для chat_id {chat_id}: {e} \n Вот "
                                  f"здесь Мы не можем проверить вашу подписку на канал")
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


#//////////////////////////////////
#проверить работу функции
# Основная функция проверки статуса подписки пользователя
async def update_subscription_status(chat_id, days_since_registration, db, bot):
    """
    Обновляет статус подписки пользователя в зависимости от количества дней с момента регистрации.
    """
    try:
        # Получаем текущий статус подписки и статус уведомлений из базы данных
        logging.info(
            f"Проверяем статус подписки для пользователя {chat_id}, зарегистрирован {days_since_registration} дней.")
        cursor = await db.execute('''
            SELECT subscription_status, is_notification, date_expire_of_paid_subscription
            FROM users
            WHERE chat_id = ?
        ''', (chat_id,))
        result = await cursor.fetchone()

        if result:
            current_status, is_notification, date_expire_of_paid_subscription = result
            logging.info(
                f"Текущий статус: {current_status}, уведомления: {is_notification}, срок подписки: {date_expire_of_paid_subscription} для пользователя {chat_id}.")

            # Если статус активен
            if current_status == "active":
                await check_active_paid_subscription_bot(chat_id, date_expire_of_paid_subscription, bot, db)
            # Если статус "new_user", проверяем сколько дней прошло
            elif current_status == "new_user":
                await check_count_days_new_user(chat_id, days_since_registration, is_notification,db, bot,)
            # Если статус "waiting_pending"
            elif current_status == "waiting_pending":
                txt="закоментил код надо раскоментить "
                #await notification_after_expire_free_trial(chat_id, bot, database)
            # Если статус "blocked"
            elif current_status == "blocked":
                logging.info(f"Пользователь {chat_id} уже заблокирован.")
        else:
            logging.error(f"Статус подписки для chat_id {chat_id} не найден в базе данных.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении статуса подписки для chat_id {chat_id}: {e}")
        await send_admin_log(bot, f"Ошибка при обновлении статуса подписки для chat_id {chat_id}: {e}")


# Подфункция для проверки активной подписки
async def check_active_paid_subscription_bot(chat_id, date_expire_of_paid_subscription, bot, db):
    """
    Проверяет, закончилась ли платная подписка у пользователя, если статус "active".
    Если подписка истекла, уведомляет пользователя и изменяет статус.
    """
    try:
        if date_expire_of_paid_subscription:
            date_expire = datetime.strptime(date_expire_of_paid_subscription, "%Y-%m-%d")
            current_date = datetime.now()

            if current_date > date_expire:
                logging.info(
                    f"Платная подписка пользователя {chat_id} истекла {date_expire}. Меняем статус на 'waiting_pending'.")
                await db.execute('''
                    UPDATE users
                    SET subscription_status = 'waiting_pending'
                    WHERE chat_id = ?
                    WHERE chat_id = ?
                ''', (chat_id,))
                await db.commit()
                # Уведомляем пользователя
                await bot.send_message(chat_id,
                                       "Ваша платная подписка закончилась. Необходимо оплатить, чтобы продолжить пользоваться VPN.",reply_markup=create_payment_button())
            else:
                logging.info(f"Подписка пользователя {chat_id} активна до {date_expire}.")
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки у пользователя {chat_id}: {e}")
        await send_admin_log(bot,f"Ошибка при проверке подписки у пользователя {chat_id}: {e}")


# Подфункция для проверки, сколько дней прошло с регистрации для new_user
async def check_count_days_new_user(chat_id, days_since_registration, is_notification, db, bot):
    """
    Проверяет, если прошло больше 14 дней с регистрации для нового пользователя и обновляет статус.
    """
    try:
        if days_since_registration > 14:
            logging.info(f"Пользователь {chat_id} пользуется больше 14 дней. Меняем статус на 'waiting_pending'.")
            await db.execute('''
                UPDATE users
                SET subscription_status = 'waiting_pending', date_expire_free_trial = ?
                WHERE chat_id = ?
            ''', (datetime.now().strftime("%Y-%m-%d"), chat_id))
            await db.commit()
            # Уведомляем пользователя о необходимости оплаты
            #раскоменетить
            #await notification_after_expire_free_trial(chat_id, bot, database)
        else:
            logging.info(f"Пользователь {chat_id} ещё на пробном периоде: {days_since_registration} дней.")
    except Exception as e:
        logging.error(f"Ошибка при проверке статуса нового пользователя {chat_id}: {e}")


# Функция оповещения пользователя об окончании пробного периода
async def notification_after_expire_free_trial(chat_id, bot, db):
    """
    Оповещает пользователя о необходимости оплаты после окончания пробного периода.
    Если пользователь был уведомлен 3 раза, меняем статус на 'blocked'.
    """
    try:
        # Извлекаем текущее значение is_notification из базы данных
        cursor = await db.execute('''
            SELECT is_notification
            FROM users
            WHERE chat_id = ?
        ''', (chat_id,))
        result = await cursor.fetchone()

        if result is None:
            logging.error(f"Пользователь с chat_id {chat_id} не найден в базе данных.")
            return

        is_notification = result[0]  # Берем значение is_notification из базы данных

        if is_notification < 3:
            try:
                # Попытка отправить уведомление
                #await bot.send_message(chat_id, "Ваш пробный период истек. Пожалуйста, оплатите подписку.",reply_markup=create_payment_button(chat_id))
                logging.info(f"Уведомление отправлено пользователю {chat_id}.")
                await send_admin_log(bot, f"Уведомление о истечении срока должно отправиься но я закоментил код отправлено пользователю {chat_id}.")

            except Exception as e:
                logging.error(f"Ошибка при уведомлении пользователя {chat_id}: {e}")
                await send_admin_log(bot,f"Ошибка при уведомлении пользователя {chat_id}: {e}")

            # Увеличиваем счётчик уведомлений даже при ошибках
            is_notification += 1
            await db.execute('''
                UPDATE users
                SET is_notification = ?
                WHERE chat_id = ?
            ''', (is_notification, chat_id,))
            await db.commit()
        else:
            logging.info(f"Пользователь {chat_id} был уведомлён 3 раза. Меняем статус на 'blocked'.")
            await db.execute('''
                UPDATE users
                SET subscription_status = 'blocked'
                WHERE chat_id = ?
            ''', (chat_id,))
            await db.commit()
            await send_admin_log(bot, f"Пользователь {chat_id} был заблокирован. Требуется ограничить доступ.")
    except TelegramForbiddenError:
        logging.error(f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
        await send_admin_log(bot,f"Бот заблокирован пользователем {chat_id}, уведомление не отправлено.")
    except Exception as e:
        logging.error(f"Ошибка при уведомлении пользователя {chat_id}: {e}")


