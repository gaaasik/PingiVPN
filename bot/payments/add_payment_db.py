from pathlib import Path
import os
from dotenv import load_dotenv
import aiosqlite




load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))

async def test_update_tolsemenovv_has_paid_subscription_db(status):
    chat_id = 1388513042
    conn = await aiosqlite.connect(database_path_local)
    await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
    print(conn)
    await conn.commit()
    await conn.close()

async def update_has_paid_subscription_db(status, chat_id):
    conn = await aiosqlite.connect(database_path_local)
    await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
    print(conn)
    await conn.commit()
    await conn.close()



async def check_has_paid_subscription_db(chat_id):
    conn = await aiosqlite.connect(database_path_local)

    async with conn.execute("SELECT has_paid_subscription FROM users WHERE chat_id = ?", (chat_id,)) as cursor:
        user = await cursor.fetchone()  # Получаем одну строку результата
    await conn.close()  # Закрываем соединение
    print("user[0]//////////////////////")
    print(user[0])
    return user[0]
