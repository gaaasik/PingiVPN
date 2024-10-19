import datetime

import aiosqlite

from bot.database.db import database_path_local

from datetime import datetime




async def add_user_db(chat_id: int, user_name: str, referrer_id: int = None):
    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Сохраняем текущее время в формате строки

    async with aiosqlite.connect(database_path_local) as conn:
        try:
            # Сначала проверяем, существует ли пользователь с таким chat_id
            cursor = await conn.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
            existing_user = await cursor.fetchone()

            if existing_user:
                print(f"Пользователь с chat_id {chat_id} уже существует.")
                return




            text_defoult = ""


            # Если пользователя нет, добавляем его
            if referrer_id:
                await conn.execute(
                    '''
                    INSERT INTO users (chat_id, user_name, registration_date, referrer_id)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (chat_id, user_name, registration_date, referrer_id)
                )
                await conn.execute(
                    '''
                    INSERT INTO users_key (chat_id, count_key)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (chat_id, 0, text_defoult)
                )



            else:
                await conn.execute(
                    '''
                    INSERT INTO users (chat_id, user_name, registration_date)
                    VALUES (?, ?, ?)
                    ''',
                    (chat_id, user_name, registration_date)
                )
                await conn.execute(
                    '''
                    INSERT INTO users_key (chat_id, count_key)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (chat_id, 0)
                )

            # Коммит транзакции
            await conn.commit()
            print(f"Пользователь с chat_id {chat_id} успешно добавлен.")

        except Exception as e:
            print(f"Ошибка при добавлении пользователя с chat_id {chat_id}: {e}")

        finally:
            await conn.close()  # Закрываем соединение после завершения работы с БД




# Функция для получения статуса пользователя
async def get_user_registration_date_and_username_db(chat_id):
    async with aiosqlite.connect(database_path_local) as db:
        # Проверяем тип данных chat_id и конвертируем его при необходимости
        if isinstance(chat_id, str) and chat_id.isdigit():
            chat_id = int(chat_id)  # Приводим к числу, если строка содержит цифры
        elif not isinstance(chat_id, int):
            raise ValueError(f"Неподдерживаемый тип данных для chat_id: {type(chat_id)}")

        # Выполняем запрос к базе данных
        cursor = await db.execute(
            "SELECT registration_date, days_since_registration, user_name, is_subscription_on_channel FROM users WHERE chat_id = ?",
            (chat_id,))
        result = await cursor.fetchone()

        # Проверяем, найден ли пользователь
        if result:
            return result  # Возвращаем только subscription_status
        else:
            return None  # Возвращаем None, если пользователь не найден
