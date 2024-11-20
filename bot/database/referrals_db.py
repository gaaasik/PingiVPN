import aiosqlite
import logging
from datetime import datetime

from bot.payments2.payments_handler_redis import db_path

logging.basicConfig(level=logging.INFO)


async def process_referral_start(new_chat_id: int, referrer_id: int = None):
    """
    Обрабатывает запуск команды /start с аргументом реферального ID.
    :param db_path: Путь к базе данных.
    :param new_chat_id: ID нового пользователя, который присоединился по реферальной ссылке.
    :param referrer_id: ID пользователя, который пригласил нового (None, если не указан).
    """


    async with aiosqlite.connect(db_path) as db:
        # Проверяем, существует ли запись для нового пользователя
        async with db.execute(
                "SELECT 1 FROM referrals WHERE referral_new_chat_id = ?", (new_chat_id,)
        ) as cursor:
            if await cursor.fetchone():
                logging.info(f"Реферальная запись уже существует для пользователя: {new_chat_id}")
                return  # Если запись существует, завершаем

        # Создаем новую реферальную запись
        await db.execute(
            '''
            INSERT INTO referrals (referral_old_chat_id, referral_new_chat_id, date_referred, referral_status, bonus_status)
            VALUES (?, ?, ?, 'invited', 'no_bonus')
            ''',
            (referrer_id, new_chat_id, datetime.now())
        )
        await db.commit()
    logging.info(f"Создана новая реферальная запись: {referrer_id} пригласил {new_chat_id}.")
