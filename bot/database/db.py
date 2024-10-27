import logging
from pathlib import Path

import aiosqlite
import os
import datetime
from datetime import datetime

import pytz
from aiogram import Bot
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))

moscow_tz = pytz.timezone('Europe/Moscow')


# Функция для получения текущего времени по Москве
def get_moscow_time():
    return datetime.now(moscow_tz)


async def get_users_with_days_since_registration(min_days: int = 14):
    """
    Возвращает список пользователей, у которых количество пройденных дней с момента регистрации >= min_days.

    :param min_days: Минимальное количество дней с момента регистрации (по умолчанию 21).
    :return: Список пользователей, соответствующих критерию.
    """
    async with aiosqlite.connect(database_path_local) as db:
        # Выполняем запрос для поиска пользователей с количеством дней >= min_days
        async with db.execute(
                "SELECT id, user_name, days_since_registration, registration_date FROM users WHERE days_since_registration >= ?",
                (min_days,)
        ) as cursor:
            users = await cursor.fetchall()

    return users  # Возвращаем список пользователей


async def drop_table(database_path: str, table_name: str):
    """
    Удаляет таблицу из базы данных.

    :param database_path: Путь к файлу базы данных.
    :param table_name: Название таблицы, которую нужно удалить.
    """
    if not table_name:
        print("Необходимо указать название таблицы.")
        return

    async with aiosqlite.connect(database_path) as conn:
        try:
            # Выполняем команду удаления таблицы
            await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            await conn.commit()
            print(f"Таблица {table_name} успешно удалена.")
        except Exception as e:
            print(f"Ошибка при удалении таблицы {table_name}: {e}")


async def init_db(database_path: str):
    if not os.path.exists(database_path_local):
        print(f"Файл базы данных не найден по пути: {database_path_local}")
    db_directory = os.path.dirname(database_path)
    if db_directory and not os.path.exists(db_directory):
        os.makedirs(db_directory)

    conn = await aiosqlite.connect(database_path)

    # Добавляем новые столбцы, если они не существуют
    await add_device_column(conn)
    await add_is_subscribed_column(conn)
    await add_vpn_usage_start_date_column(conn)
    await add_traffic_used_column(conn)
    await add_columns_to_users_sub(conn)
    #await calculate_days_and_update_status(conn)
    await add_is_notification_column(conn)
    #await get_users_with_days_since_registration()
    await add_feedback_status_column(conn)
    await add_ip_columns(conn)
    await add_days_after_pay(conn)
    await add_columns_in_db(conn, "date_payment_subscription")
    await add_columns_in_db(conn, "date_expire_free_trial")
    await add_columns_in_db(conn, "email")

    # Создание таблицы users с новыми полями
    await conn.execute('''
               CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   chat_id INTEGER UNIQUE,
                   user_name TEXT,
                   registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   referrer_id INTEGER,  -- Поле для хранения ID пригласившего пользователя
                   device TEXT,  -- Поле для устройства
                   is_subscribed BOOLEAN DEFAULT 0,  -- Поле для отслеживания подписки
                   date_payment_subscription TIMESTAMP,  -- Дата начала использования VPN
                   traffic_used INTEGER DEFAULT 0,  -- Потраченный трафик (в мегабайтах)
                   has_paid_subscription INTEGER NOT NULL DEFAULT 0,  -- Новое поле для оплаты подписки
                   subscription_status TEXT DEFAULT 'new_user',  -- Новое поле для статуса подписки
                   days_since_registration INTEGER DEFAULT 0,  -- Новое поле для количества дней с момента регистрации
                   FOREIGN KEY(referrer_id) REFERENCES users(id)
               )
           ''')

    # Создание остальных таблиц
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'free'
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(referrer_id) REFERENCES users(id),
            FOREIGN KEY(referred_id) REFERENCES users(id)
        )
    ''')

    await conn.commit()
    return conn


async def add_user(chat_id: int, user_name: str, referrer_id: int = None):
    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Сохраняем текущее время в формате строки

    async with aiosqlite.connect(database_path_local) as conn:
        try:
            # Сначала проверяем, существует ли пользователь с таким chat_id
            cursor = await conn.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
            existing_user = await cursor.fetchone()

            if existing_user:
                print(f"Пользователь с chat_id {chat_id} уже существует.")
                return

            # Если пользователя нет, добавляем его
            if referrer_id:
                await conn.execute(
                    '''
                    INSERT INTO users (chat_id, user_name, registration_date, referrer_id)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (chat_id, user_name, registration_date, referrer_id)
                )
            else:
                await conn.execute(
                    '''
                    INSERT INTO users (chat_id, user_name, registration_date)
                    VALUES (?, ?, ?)
                    ''',
                    (chat_id, user_name, registration_date)
                )

            # Коммит транзакции
            await conn.commit()
            print(f"Пользователь с chat_id {chat_id} успешно добавлен.")

        except Exception as e:
            print(f"Ошибка при добавлении пользователя с chat_id {chat_id}: {e}")

        finally:
            await conn.close()  # Закрываем соединение после завершения работы с БД


async def get_user_by_telegram_id(chat_id: int):
    async with aiosqlite.connect(database_path_local) as conn:
        cursor = await conn.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
        user = await cursor.fetchone()  # Получаем одну строку (пользователя) из результата запроса
        return user  # Возвращаем информацию о пользователе или None, если не найден


async def get_all_users():
    async with aiosqlite.connect(database_path_local) as conn:
        async with conn.execute('SELECT * FROM users') as cursor:
            users = await cursor.fetchall()
    return users


# async def get_user_registration_date_and_username(user_id: int):
#     async with aiosqlite.connect(database_path_local) as conn:
#         async with conn.execute('SELECT registration_date, user_name FROM users WHERE chat_id = ?',
#                                 (user_id,)) as cursor:
#             user = await cursor.fetchone()
#             if user:
#                 registration_date, user_name = user
#                 return registration_date, user_name
#     return None


async def add_user_question(chat_id: int, user_id: int, question_text: str):
    async with aiosqlite.connect(database_path_local) as conn:
        await conn.execute(
            'INSERT INTO user_questions (chat_id, user_id, question_text) VALUES (?, ?, ?)',
            (chat_id, user_id, question_text)
        )
        await conn.commit()


# //////////////////////////////////////////////////////////////////
async def add_referral(referrer_id: int, referred_id: int):
    async with aiosqlite.connect(database_path_local) as conn:
        # Проверяем, есть ли уже столбец referrer_id в таблице
        async with conn.execute("PRAGMA table_info(users)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

        if "referrer_id" not in column_names:
            # Добавляем новый столбец referrer_id в таблицу users
            await conn.execute('ALTER TABLE users ADD COLUMN referrer_id INTEGER')

        await conn.execute(
            'INSERT INTO referrals (referrer_id, referred_id, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)',
            (referrer_id, referred_id)
        )

        await conn.commit()


async def get_user_count():
    """Подсчет количества зарегистрированных пользователей"""
    async with aiosqlite.connect(database_path_local) as conn:
        async with conn.execute('SELECT COUNT(*) FROM users') as cursor:
            user_count = await cursor.fetchone()
            return user_count[0]


# Получаем время последней проверки подписки
async def get_last_subscription_check(chat_id):
    conn = await aiosqlite.connect(database_path_local)
    cursor = await conn.execute("SELECT last_subscription_check FROM users WHERE chat_id = ?", (chat_id,))
    result = await cursor.fetchone()
    await conn.close()
    return result[0] if result else None


# Обновляем время последней проверки подписки
async def update_last_subscription_check(chat_id):
    conn = await aiosqlite.connect(database_path_local)
    await conn.execute("UPDATE users SET last_subscription_check = ? WHERE chat_id = ?",
                       (datetime.datetime.now(), chat_id))
    await conn.commit()
    await conn.close()


# Получаем статус подписки пользователя

async def get_user_subscription_status(chat_id):
    conn = await aiosqlite.connect(database_path_local)
    cursor = await conn.execute("SELECT subscription_status FROM users WHERE chat_id = ?", (chat_id,))
    result = await cursor.fetchone()
    await conn.close()
    print("result[0]", result[0])
    return result[0] if result else False


# Обновляем статус подписки
async def update_user_subscription_status(chat_id, is_subscribed):
    conn = await aiosqlite.connect(database_path_local)
    await conn.execute("UPDATE users SET is_subscribed = ? WHERE chat_id = ?", (is_subscribed, chat_id))
    await conn.commit()
    await conn.close()


async def add_columns_to_users_sub(conn):
    """Добавляем необходимые поля в таблицу users, если их еще нет."""
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `has_paid_subscription` нет, то добавляем его
    if not any(column[1] == "has_paid_subscription" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN has_paid_subscription INTEGER NOT NULL DEFAULT 0''')
        await conn.commit()
        print("Колонка 'has_paid_subscription' добавлена в таблицу users.")
    else:
        print("Колонка 'has_paid_subscription' уже существует.")

    # Если столбца `subscription_status` нет, то добавляем его
    if not any(column[1] == "subscription_status" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'new_user' ''')
        await conn.commit()
        print("Колонка 'subscription_status' добавлена в таблицу users.")
    else:
        print("Колонка 'subscription_status' уже существует.")

    # Если столбца `days_since_registration` нет, то добавляем его
    if not any(column[1] == "days_since_registration" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN days_since_registration INTEGER DEFAULT 0''')
        await conn.commit()
        print("Колонка 'days_since_registration' добавлена в таблицу users.")
    else:
        print("Колонка 'days_since_registration' уже существует.")


async def add_device_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `device` нет, то добавляем его
    if not any(column[1] == "device" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN device TEXT''')
        await conn.commit()
        print("Колонка 'device' добавлена в таблицу users.")
    else:
        print("Колонка 'device' уже существует.")


async def add_days_after_pay(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `is_subscribed` нет, то добавляем его
    if not any(column[1] == "days_after_pay" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN days_after_pay  TIMESTAMP''')
        await conn.commit()
        print("Колонка 'days_after_pay' добавлена в таблицу users.")
    else:
        print("Колонка 'days_after_pay' уже существует.")


async def add_is_subscribed_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `is_subscribed` нет, то добавляем его
    if not any(column[1] == "is_subscribed" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT 0''')
        await conn.commit()
        print("Колонка 'is_subscribed' добавлена в таблицу users.")
    else:
        print("Колонка 'is_subscribed' уже существует.")


async def add_vpn_usage_start_date_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `vpn_usage_start_date` нет, то добавляем его
    if not any(column[1] == "vpn_usage_start_date" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN vpn_usage_start_date TIMESTAMP''')
        await conn.commit()
        print("Колонка 'vpn_usage_start_date' добавлена в таблицу users.")
    else:
        print("Колонка 'vpn_usage_start_date' уже существует.")


async def add_traffic_used_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `traffic_used` нет, то добавляем его
    if not any(column[1] == "traffic_used" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN traffic_used INTEGER DEFAULT 0''')
        await conn.commit()
        print("Колонка 'traffic_used' добавлена в таблицу users.")
    else:
        print("Колонка 'traffic_used' уже существует.")


async def who_have_expired_trial(conn):
    # SQL-запрос для нахождения пользователей с более чем 20 днями с даты регистрации
    query = '''
        SELECT chat_id, user_name, registration_date, 
               (julianday('now') - julianday(registration_date)) AS days_since_registration
        FROM users
        WHERE days_since_registration > 20
    '''

    cursor = await conn.execute(query)
    users_with_expired_trial = await cursor.fetchall()

    # Пример: Выводим всех пользователей с истекшим пробным периодом
    for user in users_with_expired_trial:
        chat_id, user_name, registration_date, days_since_registration = user
        print(
            f"Пользователь {user_name} (ID: {chat_id}) зарегистрировался {registration_date}, прошло {int(days_since_registration)} дней.")

    return users_with_expired_trial


# Функция для получения статуса пользователя
async def get_user_registration_date_and_username(chat_id):
    async with aiosqlite.connect(database_path_local) as db:
        # Проверяем тип данных chat_id и конвертируем его при необходимости
        if isinstance(chat_id, str) and chat_id.isdigit():
            chat_id = int(chat_id)  # Приводим к числу, если строка содержит цифры
        elif not isinstance(chat_id, int):
            raise ValueError(f"Неподдерживаемый тип данных для chat_id: {type(chat_id)}")

        # Выполняем запрос к базе данных
        cursor = await db.execute(
            "SELECT registration_date, days_since_registration, user_name, subscription_status FROM users WHERE chat_id = ?",
            (chat_id,))
        result = await cursor.fetchone()

        # Проверяем, найден ли пользователь
        if result:
            return result  # Возвращаем только subscription_status
        else:
            return None  # Возвращаем None, если пользователь не найден


async def add_feedback_status_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Проверяем, существует ли колонка feedback_status
    if not any(column[1] == "feedback_status" for column in columns):
        # Добавляем колонку feedback_status
        await conn.execute('''ALTER TABLE users ADD COLUMN feedback_status TEXT DEFAULT 'new_user' ''')
        await conn.commit()
        print("Колонка 'feedback_status' добавлена в таблицу users.")
    else:
        print("Колонка 'feedback_status' уже существует.")


# Функция для обновления статуса обратной связи в базе данных
async def set_feedback_status(bot, chat_id: int, status: str):
    """
    Обновляет значение поля feedback_status для пользователя с указанным chat_id.

    :param bot: Экземпляр бота для отправки сообщений или выполнения других действий
    :param chat_id: Идентификатор пользователя (chat_id)
    :param status: Статус, который нужно обновить ('excellent', 'bad', 'cant_connect')
    """
    if status not in ['excellent', 'bad', 'cant_connect']:
        print(f"Недопустимый статус: {status}")
        return

    try:
        # Открываем соединение с базой данных
        async with aiosqlite.connect(database_path_local) as conn:
            # Выполняем обновление поля feedback_status для пользователя с указанным chat_id
            await conn.execute('''
                UPDATE users
                SET feedback_status = ?
                WHERE chat_id = ?
            ''', (status, chat_id))

            # Подтверждаем изменения
            await conn.commit()

            print(f"Статус {status} успешно установлен для пользователя с chat_id: {chat_id}")

    except Exception as e:
        print(f"Ошибка при обновлении статуса для пользователя с chat_id {chat_id}: {e}")


# Функция для получения статуса обратной связи пользователя
async def get_feedback_status(chat_id: int) -> str:
    """
    Извлекает значение поля feedback_status для пользователя с указанным chat_id.

    :param chat_id: Идентификатор пользователя (chat_id)
    :return: Статус обратной связи ('excellent', 'bad', 'cant_connect') или None, если пользователь не найден
    """
    try:
        # Открываем соединение с базой данных
        async with aiosqlite.connect(database_path_local) as conn:
            # Выполняем запрос на получение поля feedback_status для пользователя с указанным chat_id
            cursor = await conn.execute('''
                SELECT feedback_status
                FROM users
                WHERE chat_id = ?
            ''', (chat_id,))

            # Извлекаем результат
            row = await cursor.fetchone()

            # Проверяем, найден ли пользователь
            if row:
                feedback_status = row[0]  # feedback_status находится в первом элементе
                print(f"Статус обратной связи для chat_id {chat_id}: {feedback_status}")
                return feedback_status
            else:
                print(f"Пользователь с chat_id {chat_id} не найден.")
                return None

    except Exception as e:
        print(f"Ошибка при получении статуса для пользователя с chat_id {chat_id}: {e}")
        return None


async def add_is_notification_column(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Если столбца `is_notification` нет, то добавляем его
    if not any(column[1] == "is_notification" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN is_notification BOOLEAN DEFAULT 0''')
        await conn.commit()
        print("Колонка 'is_notification' добавлена в таблицу users.")
    else:
        print("Колонка 'is_notification' уже существует.")


async def add_ip_columns(conn):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()

    # Добавляем колонку для хранения частного IP-адреса пользователя
    if not any(column[1] == "private_ip" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN private_ip TEXT''')
        print("Колонка 'private_ip' добавлена в таблицу users.")

    # Добавляем колонку для хранения IP-адреса сервера
    if not any(column[1] == "server_ip" for column in columns):
        await conn.execute('''ALTER TABLE users ADD COLUMN server_ip TEXT''')
        print("Колонка 'server_ip' добавлена в таблицу users.")

    await conn.commit()

    # Функция для обновления информации о платеже в базе данных с московским временем


async def add_columns_in_db(conn, name_column):
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()
    # Добавляем колонку для хранения частного IP-адреса пользователя
    if not any(column[1] == name_column for column in columns):
        await conn.execute(f'''ALTER TABLE users ADD COLUMN {name_column} private_ip TEXT''')
        print(f"Колонка {name_column} добавлена в таблицу users.")

    await conn.commit()


async def update_payment_status(payment_id, user_id, amount, currency, status):
    async with aiosqlite.connect(database_path_local) as conn:
        cursor = await conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
        payment_exists = await cursor.fetchone()  # Используем fetchone для проверки наличия записи
        await cursor.close()  # Закрываем курсор после выполнения запроса

        moscow_time = get_moscow_time()

        if payment_exists:
            await conn.execute("""
                UPDATE payments
                SET status = ?, updated_at = ?
                WHERE payment_id = ?
            """, (status, moscow_time, payment_id))
        else:
            await conn.execute("""
                INSERT INTO payments (user_id, payment_id, amount, currency, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, payment_id, amount, currency, status, moscow_time, moscow_time))

        await conn.commit()


# Асинхронное обновление подписки
async def update_user_subscription_db(user_id: int):
    """Асинхронно обновляет статус подписки пользователя в базе данных."""
    db_path = os.getenv('database_path_local')  # Путь к базе данных
    days_after_pay = 0
    try:
        # Добавляем 30 дней к текущей дате
        #date_expire_of_paid_subscription = datetime.now() + # тут ошибка datetime.timedelta(days=30)
        # Устанавливаем соединение с базой данных
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                UPDATE users
                SET subscription_status = 'active',
                    has_paid_subscription = 1,
                    date_payment_subscription = ?,
                    days_after_pay = ?
                WHERE chat_id = ?
            """, (datetime.now(), days_after_pay, user_id), )
            # Сохраняем изменения
            await conn.commit()
            logging.info(f"Подписка обновлена для пользователя с ID {user_id}.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении подписки для пользователя с ID {user_id}: {e}")


async def check_24_hour_db(user_id: int):
    async with aiosqlite.connect(database_path_local) as db:
        #Получаем текущую дату и время
        current_time = datetime.now()
        async with db.execute(
                "SELECT user_id, date_registration, date_payment_subscription, is_subscribed, has_paid_subscription, subscription_status,days_after_pay FROM users") as cursor:
            rows = await cursor.fetchall()

            row: object
            for row in rows:
                user_id, date_registration, date_payment_subscription, is_subscribed, has_paid_subscription, subscription_status, days_after_pay = row
                day = await get_days_since_registration_db(user_id)

async def get_days_since_registration_db(chat_id: int) -> int:
    """
    Функция для получения количества дней между сегодняшней датой
    и датой регистрации пользователя в базе данных.

    :param chat_id: Идентификатор чата пользователя.
    :return: Количество дней с момента регистрации пользователя.
    """
    try:
        print(f"Пытаемся подключиться к базе данных: {database_path_local}")
        async with aiosqlite.connect(database_path_local) as conn:
            print(f"Подключение к базе данных установлено. Получаем дату регистрации для chat_id: {chat_id}")

            # Запрашиваем дату регистрации пользователя по его chat_id
            async with conn.execute("SELECT registration_date FROM users WHERE chat_id = ?", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                await conn.commit()  # Сохраняем изменения (на всякий случай, хотя здесь это не обязательно)
                print(f"Результат запроса для chat_id {chat_id}: {row}")

                if row is None:
                    # Если пользователь с таким chat_id не найден в базе данных
                    print(f"Пользователь с chat_id {chat_id} не найден в базе данных.")
                    return -1

                date_registration_str = row[0]
                print(f"Дата регистрации пользователя: {date_registration_str}")
                date_registration_str = date_registration_str.split('.')[0]
                # Преобразуем дату регистрации из строки в объект datetime
                # Извлекаем только дату, игнорируя время
                date_registration = datetime.strptime(date_registration_str, "%Y-%m-%d %H:%M:%S").date()
                print(f"Дата регистрации преобразована в объект: {date_registration}")

                # Получаем текущую дату
                current_date = datetime.now().date()
                print(f"Текущая дата: {current_date}")
                разобраться с датами и дальше тестировать оплату с тестовым магазином и с оплатой и чеками

                # Вычисляем количество дней с момента регистрации
                days_since_registration = (current_date - date_registration).days
                print(f"Количество дней с момента регистрации: {days_since_registration}")

                # Обновляем запись в базе данных
                print(f"Обновляем количество дней с момента регистрации для chat_id: {chat_id}")
                await conn.execute("""
                    UPDATE users
                    SET days_after_pay = ?
                    WHERE chat_id = ?
                """, (days_since_registration, chat_id))
                await conn.commit()
                print(f"Данные успешно обновлены для chat_id: {chat_id}")

                return days_since_registration

    except Exception as e:
        print(f"Ошибка при получении даты регистрации: {e}")
        return -1



#is_subscribed, date_payment_subscription,has_paid_subscription,subscription_status,days_after_pay
# async def check_24_hour_db(bot: Bot):
#     """
#     Функция проверяет записи в базе данных и обновляет статус подписки пользователей,
#     если прошло 24 часа с момента последнего платежа.
#     """
#     async with aiosqlite.connect(database_path_local) as database:
#
#         # Получаем текущую дату и время
#         current_time = datetime.now()
#
#         # Получаем все записи из базы данных для проверки
#         async with database.execute(
#                 "SELECT user_id, date_payment_subscription, is_subscribed, has_paid_subscription, subscription_status,days_after_pay FROM users") as cursor:
#             rows = await cursor.fetchall()
#
#             row: object
#             for row in rows:
#                 user_id, date_payment_subscription, is_subscribed, has_paid_subscription,subscription_status, days_after_pay = row
#
#              нужно записать в поле days_after_pay -  (date now - date_payment_subscription)
#                 если days_after_pay = 1 то..
#            # has_paid_subscription - проверяем days_after_pay - 1
#
#             # нужно уменшить количетсво дней - 1 days_after_pay
#             # is_subscribed - проверить подписку - отправить сообщение если не подписан
#             # если количество дней days_after_pay=1 - нужно отправить сообщение пользователю о том что подписка завтра закончитсяи изменить статус на waiting_pending
#             #     если 0 отправлем сообщение оплатите подписку - и меняем has_paid_subscription=0 ,subscription_status = expired


# еслм days_after_pay = 1 (time_left_after_payment)то отправляем предупреждающее сообщение пользователю об окончании подписки


# # Сохраняем изменения в базе данных
# await database.commit()

# Функция сохранения email в базу данных
async def save_user_email_to_db(user_id: int, email: str):
    """
    Функция для сохранения email пользователя в базу данных.
    :param user_id: ID пользователя
    :param email: email пользователя
    """
    query = """
    UPDATE users 
    SET email = ? 
    WHERE chat_id = ?
    """

    try:
        async with aiosqlite.connect(database_path_local) as db:
            await db.execute(query, (email, user_id))
            await db.commit()  # Подтверждаем изменения в базе данных
            print(f"Email {email} для пользователя {user_id} успешно сохранён.")
    except Exception as e:
        print(f"Ошибка при сохранении email для пользователя {user_id}: {e}")