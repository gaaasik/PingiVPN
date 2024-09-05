import aiosqlite
import os
import datetime

import bot

# Путь к конфигурационным файлам
CONFIGS_DIR = r'C:\PycharmProjects\VPN BOT\configs'
BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')


# async def delete_user(telegram_id: int):
#     async with aiosqlite.connect('vpn_bot.db') as conn:
#         # Получаем информацию о пользователе
#         user = await get_user_by_telegram_id(telegram_id)
#         if user:
#             phone_number = user[2]  # предполагаем, что номер телефона находится в третьем столбце
#
#             # Путь к папке пользователя
#             user_dir = os.path.join(CONFIGS_DIR, phone_number)
#             user_config_file = os.path.join(user_dir, f"{phone_number}.conf")
#
#             # Проверяем, существует ли файл
#             if os.path.exists(user_config_file):
#                 # Переименовываем файл обратно в 'free_config'
#                 base_free_config_name = os.path.basename(user_config_file).replace(phone_number, 'free_config')
#                 new_free_config_path = os.path.join(BASE_CONFIGS_DIR, base_free_config_name)
#                 os.rename(user_config_file, new_free_config_path)
#
#                 # Переименовываем QR-код обратно в 'free_config'
#                 user_qr_file = os.path.splitext(user_config_file)[0] + '.png'
#                 base_free_qr_name = os.path.basename(user_qr_file).replace(phone_number, 'free_config')
#                 new_free_qr_path = os.path.join(BASE_CONFIGS_DIR, base_free_qr_name)
#                 os.rename(user_qr_file, new_free_qr_path)
#
#         # Удаление пользователя из базы данных
#         await conn.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
#         await conn.execute('DELETE FROM connections WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)', (telegram_id,))
#         await conn.commit()
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
    db_directory = os.path.dirname(database_path)
    if db_directory and not os.path.exists(db_directory):
        os.makedirs(db_directory)

    conn = await aiosqlite.connect(database_path)

    # Создание таблицы users
    await conn.execute('''
         CREATE TABLE IF NOT EXISTS users (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             chat_id INTEGER UNIQUE,
             user_name TEXT,
             registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             referrer_id INTEGER,  -- Новое поле для хранения ID пригласившего пользователя
             FOREIGN KEY(referrer_id) REFERENCES users(id)
         )
     ''')

    # Создание таблицы connections
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Создание таблицы configurations для отслеживания конфигурационных файлов
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS configurations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'free'
        )
    ''')

    # ////////// Добавление создания таблицы user_questions //////////
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # //////////////////////////////////////////////////////////////////

    # Создание таблицы referrals
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
    async with aiosqlite.connect('vpn_bot.db') as conn:
        await conn.execute(
            'INSERT INTO users (chat_id, user_name, registration_date, referrer_id) VALUES (?, ?, ?, ?)',
            (chat_id, user_name, registration_date, referrer_id)
        )
        await conn.commit()




async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect('vpn_bot.db') as conn:
        async with conn.execute('SELECT * FROM users WHERE chat_id = ?', (telegram_id,)) as cursor:
            return await cursor.fetchone()



async def get_all_users():
    async with aiosqlite.connect('vpn_bot.db') as conn:
        async with conn.execute('SELECT * FROM users') as cursor:
            users = await cursor.fetchall()
    return users


async def get_user_status(user_id: int):
    async with aiosqlite.connect('vpn_bot.db') as conn:
        async with conn.execute('SELECT registration_date, user_name FROM users WHERE chat_id = ?', (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                registration_date, user_name = user
                return registration_date, user_name
    return None

async def add_user_question(chat_id: int, user_id: int, question_text: str):
    async with aiosqlite.connect('vpn_bot.db') as conn:
        await conn.execute(
            'INSERT INTO user_questions (chat_id, user_id, question_text) VALUES (?, ?, ?)',
            (chat_id, user_id, question_text)
        )
        await conn.commit()
# //////////////////////////////////////////////////////////////////
async def add_referral(referrer_id: int, referred_id: int):
    async with aiosqlite.connect('vpn_bot.db') as conn:
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

