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

        # Завершаем транзакцию
        await db.commit()