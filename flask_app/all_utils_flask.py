import logging
import aiosqlite
from datetime import datetime
import pytz
from flask_app.config_flask_redis import DATABASE_PATH, REDIS_QUEUE
from flask_app.redis_utils import send_to_redis

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_moscow_time():
    """Получение текущего времени в часовом поясе Москвы."""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)

async def update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id):
    """Асинхронное обновление или добавление записи о платеже в таблицу payments."""
    try:
        logging.info(f"Начало обработки платежа {payment_id} для пользователя {user_id}.")

        async with aiosqlite.connect(DATABASE_PATH) as connection:
            logging.info("Соединение с базой данных установлено.")
            cursor = await connection.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
            payment_exists = await cursor.fetchone()
            moscow_time = get_moscow_time()

            if payment_exists:
                # Обновляем существующую запись
                logging.info(f"Платеж {payment_id} существует. Обновляем его статус.")
                await connection.execute('''
                    UPDATE payments
                    SET status = ?, updated_at = ?
                    WHERE payment_id = ?
                ''', (status, moscow_time, payment_id))
                logging.info(f"Обновлен статус платежа {payment_id}: {status}")
            else:
                # Вставляем новую запись
                logging.info(f"Платеж {payment_id} не найден. Добавляем новую запись.")
                await connection.execute('''
                    INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, payment_id, amount, currency, status, payment_method_id, moscow_time, moscow_time))
                logging.info(
                    f"Добавлен новый платеж: ID {payment_id}, пользователь {user_id}, сумма {amount} {currency}.")

            # Фиксируем изменения в базе данных
            await connection.commit()
            logging.info(f"Изменения для платежа {payment_id} успешно зафиксированы в базе данных.")

        # Отправка информации о платеже в Redis
        message = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": status
        }
        logging.info(f"Подготовка к отправке сообщения в Redis: {message}")

        # Печатаем сообщение перед отправкой в Redis для отладки
        print(f"Попытка отправки сообщения в Redis: {message}")

        await send_to_redis(REDIS_QUEUE, message)
        logging.info(f"Сообщение для платежа {payment_id} успешно отправлено в очередь Redis.")

    except Exception as e:
        logging.error(f"Ошибка обновления информации о платеже {payment_id} в базе данных: {e}")


async def initialize_db():
    """Асинхронная инициализация базы данных с использованием aiosqlite."""
    async with aiosqlite.connect(DATABASE_PATH) as connection:
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                payment_id TEXT UNIQUE,
                amount REAL,
                currency TEXT,
                status TEXT,
                payment_method_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        await connection.commit()
