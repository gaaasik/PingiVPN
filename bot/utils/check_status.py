import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot
import aiosqlite
from pytz import timezone

from bot.keyboards.inline import create_feedback_keyboard
from data.text_messages import attention_message

# Настройки
ADMIN_CHAT_ID = 456717505  # ID админа
TRIAL_PERIOD_DAYS = 15  # Продолжительность пробного периода
DB_PATH = Path(os.getenv('database_path_local'))  # Путь к базе данных


async def get_users_from_db():
    """Получение всех пользователей из базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id, user_name, registration_date FROM users")
        users = await cursor.fetchall()
        return users

def calculate_days_since_registration(registration_date):
    """Вычисление количества дней с даты регистрации"""
    reg_date = datetime.strptime(registration_date, "%Y-%m-%d %H:%M:%S.%f")
    current_date = datetime.now()
    return (current_date - reg_date).days

async def update_user_days_in_db(chat_id, days, db):
    """Обновление количества дней с момента регистрации"""
    await db.execute("UPDATE users SET days_since_registration = ? WHERE chat_id = ?", (days, chat_id))
    await db.commit()


async def check_db(bot: Bot):
    """Проверка базы данных, обновление дней и уведомление пользователей об окончании пробного периода"""
    print("check_db run ")
    try:
        users = await get_users_from_db()  # Получаем всех пользователей
        async with aiosqlite.connect(DB_PATH) as db:
            for user in users:
                chat_id, username, registration_date = user
                days_since_registration = calculate_days_since_registration(registration_date)

                # Обновляем количество дней с момента регистрации
                await update_user_days_in_db(chat_id, days_since_registration, db)

                # Проверяем и обновляем статус подписки
                if days_since_registration > 14:
                    # Получаем текущий статус
                    cursor = await db.execute("SELECT subscription_status FROM users WHERE chat_id = ?", (chat_id,))
                    current_status = await cursor.fetchone()

                    # Если статус ещё не "waiting_pending", обновляем и отправляем уведомление
                    if current_status and current_status[0] != 'waiting_pending':
                        await db.execute("UPDATE users SET subscription_status = 'waiting_pending' WHERE chat_id = ?",
                                         (chat_id,))
                        await db.commit()

                        # Отправляем сообщение пользователю
                        warning_message = (
                            f"Ваш пробный период истек. Пожалуйста, оплатите подписку, чтобы продолжить пользоваться VPN."
                        )
                        await bot.send_message(chat_id, warning_message)
                        print(
                            f"Статус пользователя с chat_id {chat_id} обновлен на 'waiting_pending'. Сообщение отправлено.")

    except Exception as e:
        logging.error(f"Ошибка при выполнении проверки бесплатных аккаунтов: {e}")

# Функция для проверки статуса пользователя и отправки сообщения, если статус "free"
async def check_and_notify_free_user(conn, bot: Bot, chat_id: int, message: str):
    """
    Проверяет текущий статус пользователя, отправляет сообщение, если статус 'free',
    и обновляет его на 'waiting_pending'.

    :param conn: Подключение к базе данных
    :param bot: Объект бота для отправки сообщения
    :param chat_id: Идентификатор пользователя (chat_id)
    :param message: Сообщение, которое будет отправлено пользователю
    """
    try:
        # Получаем текущий статус пользователя
        cursor = await conn.execute('''
            SELECT subscription_status
            FROM users
            WHERE chat_id = ?
        ''', (chat_id,))
        row = await cursor.fetchone()

        # Проверяем, найден ли пользователь
        if row:
            current_status = row[0]

            # Если статус 'free', отправляем сообщение и обновляем статус на 'waiting_pending'
            if current_status == 'free':
                #await bot.send_message(456717505, f"в чат {chat_id} будет отправлено {message}",reply_markup=create_feedback_keyboard())
                print(f"Сообщение отправлено пользователю с chat_id {chat_id} current_status == 'free'")

                # Обновляем статус на 'waiting_pending'
                await conn.execute('''
                    UPDATE users
                    SET subscription_status = 'waiting_pending'
                    WHERE chat_id = ?
                ''', (chat_id,))
                await conn.commit()
                print(f"Статус пользователя с chat_id {chat_id} обновлен на 'waiting_pending'")
            else:
                print(f"Пользователь с chat_id {chat_id} имеет статус: {current_status}. Сообщение не отправлено.")
        else:
            print(f"Пользователь с chat_id {chat_id} не найден.")

    except Exception as e:
        print(f"Ошибка при обработке пользователя с chat_id {chat_id}: {e}")


# Основная функция для обработки всех пользователей с пробным периодом
async def process_free_users(bot: Bot, message: str):
    conn = await aiosqlite.connect(DB_PATH)
    try:
        # Получаем пользователей, у которых статус 'free'
        cursor = await conn.execute('''
            SELECT chat_id
            FROM users
            WHERE subscription_status = 'free'
        ''')
        free_users = await cursor.fetchall()

        print(f"Пользователи со статусом 'free': {free_users}")

        # Отправляем сообщения и обновляем статусы для всех пользователей со статусом 'free'
        for user in free_users:
            chat_id = user[0]

            # Проверка и отправка сообщения пользователю с обновлением статуса
            await check_and_notify_free_user(conn, bot, chat_id, message)

        # После обработки всех пользователей, проверим еще раз, что статусы обновлены корректно
        updated_cursor = await conn.execute('''
            SELECT chat_id, subscription_status
            FROM users
            WHERE subscription_status = 'waiting_pending'
        ''')
        updated_users = await updated_cursor.fetchall()

        print(f"Пользователи с обновленным статусом 'waiting_pending': {updated_users}")

    finally:
        await conn.close()




# Пример использования
async def notify_users_with_free_status(bot: Bot):

    await process_free_users(bot, attention_message)