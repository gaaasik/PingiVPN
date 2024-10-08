# import asyncio
# import sqlite3
# from flask_app.all_utils_flask import get_moscow_time, logger, initialize_db
# from redis_utils import send_to_redis
# from  flask_app.config_flask_redis import DATABASE_PATH, REDIS_QUEUE
#
# async def update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id):
#     """Асинхронное обновление статуса платежа в базе данных."""
#     try:
#         connection = sqlite3.connect(DATABASE_PATH)
#         cursor = connection.cursor()
#         moscow_time = get_moscow_time()
#
#         cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
#         payment_exists = cursor.fetchone()
#
#         if payment_exists:
#             cursor.execute("""
#             UPDATE payments
#             SET status = ?, updated_at = ?
#             WHERE payment_id = ?
#             """, (status, moscow_time, payment_id))
#             logger.info(f"Обновлен статус платежа {payment_id}: {status}")
#         else:
#             cursor.execute("""
#             INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             """, (user_id, payment_id, amount, currency, status, payment_method_id, moscow_time, moscow_time))
#             logger.info(f"Добавлен новый платеж: ID {payment_id}, пользователь {user_id}, сумма {amount} {currency}.")
#
#         connection.commit()
#
#         # Отправка информации о платеже в Redis
#         message = {
#             "user_id": user_id,
#             "payment_id": payment_id,
#             "amount": amount,
#             "currency": currency
#         }
#         send_to_redis(REDIS_QUEUE, message)
#
#     except Exception as e:
#         logger.error(f"Ошибка обновления информации о платеже в базе данных: {e}")
#     finally:
#         connection.close()
