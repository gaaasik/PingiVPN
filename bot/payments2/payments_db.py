import os

import aiosqlite


async def reset_user_data_db(user_id):
    db_path = os.getenv('database_path_local')
    async with aiosqlite.connect(db_path) as conn:
        try:
            # Сброс данных о подписке пользователя
            await conn.execute("""
                UPDATE users
                SET has_paid_subscription = 0,
                    subscription_status = 'waiting_pending',
                    date_payment_subscription = NULL
                WHERE chat_id = ?
            """, (user_id,))

            # # Сброс данных о подписке пользователя
            # await conn.execute("""
            #                UPDATE users
            #                SET has_paid_subscription = 0,
            #                    subscription_status = 'waiting_pending',
            #                    vpn_usage_start_date = NULL
            #                WHERE chat_id = ?
            #            """, (user_id,))

            await conn.commit()
            print(f"Данные для пользователя с ID {user_id} успешно сброшены.")
        except aiosqlite.Error as e:
            print(f"Ошибка при сбросе данных: {e}")