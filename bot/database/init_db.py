import logging

import aiosqlite


# Инициализация базы данных
async def init_db(database_path: str):
    async with aiosqlite.connect(database_path) as db:
        # Начало транзакции
        await db.execute("BEGIN TRANSACTION;")

        await db.execute('''
                   CREATE TABLE IF NOT EXISTS "referrals" (
                       "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                       "referral_old_chat_id" INTEGER NOT NULL,
                       "referral_new_chat_id" INTEGER NOT NULL,
                       "date_referred" DATETIME NOT NULL,
                       "referral_status" VARCHAR NOT NULL DEFAULT 'invited',
                       "bonus_status" VARCHAR NOT NULL DEFAULT 'no_bonus',
                       "date_bonus_awarded" DATETIME,
                       FOREIGN KEY("referral_old_chat_id") REFERENCES "users"("id"),
                       FOREIGN KEY("referral_new_chat_id") REFERENCES "users"("id")
                   );
               ''')

        # Таблица user_questions
        await db.execute('''CREATE TABLE IF NOT EXISTS "user_questions" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "chat_id" INTEGER NOT NULL,
            "user_id" INTEGER NOT NULL,
            "question_text" TEXT NOT NULL,
            "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP
        );''')

        # Таблица users
        await db.execute('''CREATE TABLE IF NOT EXISTS "users" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "chat_id" INTEGER UNIQUE,
            "user_name_full" TEXT,
            "user_login" TEXT,
            "registration_date" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            "referral_old_chat_id" INTEGER,
            "device" TEXT,
            "is_subscribed_on_channel" BOOLEAN DEFAULT 0,
            "days_since_registration" INTEGER DEFAULT 0,
            "email" TEXT,
            FOREIGN KEY("referral_old_chat_id") REFERENCES "users"("id")
        );''')

        # Таблица users_key (по chat_id)
        await db.execute('''CREATE TABLE IF NOT EXISTS "users_key" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "chat_id" INTEGER UNIQUE,
            "count_key" INTEGER,
            "value_key" TEXT
        );''')

        # Таблица payments
        await db.execute('''CREATE TABLE IF NOT EXISTS "payments" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "chat_id" TEXT,
            "payment_id" TEXT,
            "amount" REAL,
            "currency" TEXT,
            "status" TEXT,
            "payment_method_id" TEXT,
            "created_at" TEXT,
            "updated_at" TEXT,
            "payment_json" TEXT
        );''')

        # Создаем или изменяем таблицу notifications
        await db.execute('''
               CREATE TABLE IF NOT EXISTS "notifications" (
                   "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                   "chat_id" INTEGER NOT NULL UNIQUE,               -- Идентификатор пользователя
                   "notification_data" JSON NOT NULL DEFAULT '{}',  -- JSON-структура для хранения всех уведомлений
                   FOREIGN KEY("chat_id") REFERENCES "users"("chat_id")
               );
           ''')

        # Таблица друзей (friends)
        await db.execute('''
                   CREATE TABLE IF NOT EXISTS "friends" (
                       "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                       "admin_chat_id" INTEGER NOT NULL,
                       "friend_chat_id" INTEGER NOT NULL,
                       "friend_username" TEXT,
                       "date_added" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       "status" VARCHAR(20) DEFAULT 'active',
                       "notes" TEXT,
                       FOREIGN KEY("admin_chat_id") REFERENCES "users"("chat_id"),
                       FOREIGN KEY("friend_chat_id") REFERENCES "users"("chat_id")
                   );
               ''')

        # Завершаем транзакцию
        await db.commit()


async def update_database(database_path: str):
    """
       Добавляет поле `active_chat` в таблицу users, если отсутствует,
       и поле `history_key` в таблицу users_key.
       """
    async with aiosqlite.connect(database_path) as db:
        # Добавление поля active_chat
        try:
            await db.execute("ALTER TABLE users ADD COLUMN active_chat BOOLEAN DEFAULT TRUE")
            await db.commit()
            print("✅ Поле `active_chat` добавлено в таблицу `users`")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️ Поле `active_chat` уже существует.")
            else:
                print(f"❌ Ошибка при добавлении `active_chat`: {e}")

    """
       Проверяет наличие столбца `has_accepted_agreement` в таблице `users`
       и добавляет его, если он отсутствует.
       """
    async with aiosqlite.connect(database_path) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN has_accepted_agreement BOOLEAN DEFAULT FALSE")
            await db.commit()
            print("✅ Поле `has_accepted_agreement` добавлено в таблицу `users`")
        except Exception as e:
            if "duplicate column" in str(e):
                print("⚠️ Поле `has_accepted_agreement` уже существует.")
            else:
                print(f"❌ Ошибка при обновлении базы данных: {e}")

            # Проверяем, существует ли таблица friends
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='friends';") as cursor:
            table_exists = await cursor.fetchone()

        if not table_exists:
            await db.execute("""
                     CREATE TABLE friends (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         admin_chat_id INTEGER NOT NULL,
                         friend_chat_id INTEGER NOT NULL,
                         friend_username TEXT,
                         date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         status VARCHAR(20) DEFAULT 'active',
                         notes TEXT,
                         FOREIGN KEY(admin_chat_id) REFERENCES users(chat_id),
                         FOREIGN KEY(friend_chat_id) REFERENCES users(chat_id)
                     );
                 """)
            await db.commit()
            print("✅ Таблица `friends` успешно создана.")
        else:
            print("⚠️ Таблица `friends` уже существует, обновление не требуется.")

    async with aiosqlite.connect(database_path) as db:
        # Проверяем, существует ли поле history_key
        async with db.execute("PRAGMA table_info(users_key);") as cursor:
            columns = [row[1] async for row in cursor]  # row[1] — имя колонки

        if "history_key" in columns:
            logging.info("Поле 'history_key' уже существует, обновление не требуется.")
            return

        # Если колонки нет, выполняем ALTER TABLE
        await db.execute("ALTER TABLE users_key ADD COLUMN history_key TEXT;")
        await db.commit()
        logging.info("Поле 'history_key' успешно добавлено в таблицу 'users_key'.")