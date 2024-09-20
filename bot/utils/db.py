from pathlib import Path

import aiosqlite
import os
import datetime

from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))



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

    # Создание таблицы users с новыми полями
    await conn.execute('''
         CREATE TABLE IF NOT EXISTS users (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             chat_id INTEGER UNIQUE,
             user_name TEXT,
             registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             referrer_id INTEGER,  -- Новое поле для хранения ID пригласившего пользователя
             device TEXT,  -- Новое поле для устройства
             is_subscribed BOOLEAN DEFAULT 0,  -- Поле для отслеживания подписки
             vpn_usage_start_date TIMESTAMP,  -- Дата начала использования VPN
             traffic_used INTEGER DEFAULT 0,  -- Потраченный трафик (в мегабайтах)
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
    registration_date = datetime.datetime.now()  # Сохраняем текущее время
    async with aiosqlite.connect(database_path_local) as conn:
        await conn.execute(
            'INSERT INTO users (chat_id, user_name, registration_date, referrer_id) VALUES (?, ?, ?, ?)',
            (chat_id, user_name, registration_date, referrer_id)
        )
        await conn.commit()




async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(database_path_local) as conn:
        async with conn.execute('SELECT * FROM users WHERE chat_id = ?', (telegram_id,)) as cursor:
            return await cursor.fetchone()



async def get_all_users():
    async with aiosqlite.connect(database_path_local) as conn:
        async with conn.execute('SELECT * FROM users') as cursor:
            users = await cursor.fetchall()
    return users


async def get_user_status(user_id: int):
    async with aiosqlite.connect(database_path_local) as conn:
        async with conn.execute('SELECT registration_date, user_name FROM users WHERE chat_id = ?', (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                registration_date, user_name = user
                return registration_date, user_name
    return None

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
    await conn.execute("UPDATE users SET last_subscription_check = ? WHERE chat_id = ?", (datetime.datetime.now(), chat_id))
    await conn.commit()
    await conn.close()

# Получаем статус подписки пользователя
async def get_user_subscription_status(chat_id):
    conn = await aiosqlite.connect(database_path_local)
    cursor = await conn.execute("SELECT is_subscribed FROM users WHERE chat_id = ?", (chat_id,))
    result = await cursor.fetchone()
    await conn.close()
    return result[0] if result else False

# Обновляем статус подписки
async def update_user_subscription_status(chat_id, is_subscribed):
    conn = await aiosqlite.connect(database_path_local)
    await conn.execute("UPDATE users SET is_subscribed = ? WHERE chat_id = ?", (is_subscribed, chat_id))
    await conn.commit()
    await conn.close()




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
