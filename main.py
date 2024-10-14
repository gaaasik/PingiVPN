import asyncio
import logging
import os
from pathlib import Path
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from bot.handlers.admin import send_admin_log
from bot.keyboards.inline import create_feedback_keyboard
from bot.payments2.payments_handler_redis import run_listening_redis_for_duration, listen_to_redis_queue
#from bot.payments2.payments_handler_redis import listen_to_redis_queue
from bot.utils.add_ip_adress import update_user_ip_info
from bot.utils.db import who_have_expired_trial, add_user#, check_24_hour_db
from bot.handlers import start, status, support, admin, share, start_to_connect, instructions, \
    device_choice, app_downloaded, file_or_qr, subscription, speedtest, user_help_request, feedback
from bot.payments2 import payments_handler_redis
from bot.utils.cache import cache_media
from bot.utils.check_status import check_db#, notify_users_with_free_status
from bot.utils.logger import setup_logger
from bot.utils.db import init_db,database_path_local
from bot.midlewares.throttling import ThrottlingMiddleware
from bot_instance import BOT_TOKEN, dp, bot
from flask_app.all_utils_flask_db import initialize_db

# Загружаем переменные окружения из файла .env
load_dotenv()

# Глобальная переменная для хранения экземпляра бота

PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
video_path = os.getenv("video_path")
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')


async def on_startup():
    """Кэширование изображений при старте"""
    image_path = os.path.join(PATH_TO_IMAGES, "Hello.png")
    print('закешировали приветственное фото')
    await cache_media(image_path, video_path)


# Функция, которая выполняется каждые 10 секунд
async def periodic_task(bot: Bot):
    # Ждем 10 секунд после старта бота
    await asyncio.sleep(1)
    while True:
        await send_admin_log(bot, "Пинг бота - прошел 1 час работы бота.")
        #await check_db(bot) # обновляет базу данных : количество дней с нами, количетсво дней платной подписки


        # , статус подписки, если закончилась подписка то меняется has_paid

        # Пример асинхронного вызова
        # await notify_users_with_free_status(bot)
        await asyncio.sleep(3600)


async def periodic_task_24_hour(bot: Bot):
    # Ждем 10 секунд после старта бота
    await asyncio.sleep(1)

    while True:
        print("Сработала функция 24 часа")
        try:
            # Сообщаем администратору о начале обновления
            await send_admin_log(bot, "Пинг бота - прошел 24 часа работы бота. Началось обновление базы данных")

            # Выполнение проверки базы данных
            await check_db(bot)

            # Уведомление об успешном завершении
            await send_admin_log(bot, "Обновление базы данных прошло успешно.")

        except Exception as e:
            # Логирование ошибки и отправка уведомления администратору
            logging.error(f"Ошибка при выполнении обновления базы данных: {e}")
            await send_admin_log(bot, f"Обновление базы данных завершилось с ошибкой: {e}")

        finally:
            # Ожидание 24 часа (86400 секунд) перед следующей проверкой
            await asyncio.sleep(86400)


async def main():

    try:
        await send_admin_log(bot, "Бот запустился")
    except Exception as e:
        logging.exception(f"Ошибка при отправке запуске очереди Redis: {e}")

    await on_startup()
    await initialize_db()

    # Пример использования:
    #add_column_to_payments("new_column_name")

    # Читаем токен бота из переменной окружения
    if not BOT_TOKEN:
        print("Ошибка: Токен не найден в .env файле!")
        return
    print(f"Токен успешно загружен: {BOT_TOKEN}")

    # Настраиваем логирование
    setup_logger("logs/bot.log")

    # Указываем путь к базе данных
    db_path = Path(os.getenv('database_path_local'))
    if not db_path.exists():
        print("Файл базы данных не найден!")
        return
    print(f"Путь к базе данных: {db_path}")
    # Инициализация бота и диспетчера

    # Инициализация базы данных SQLite
    await init_db(db_path)
    result = await add_user(111224422, "test_user")
    # Запускаем асинхронную задачу для периодической отправки сообщений админу
    asyncio.create_task(periodic_task(bot))
    asyncio.create_task(periodic_task_24_hour(bot))
    asyncio.create_task(listen_to_redis_queue(bot))  # 1 час
     # Промежуточное ПО для предотвращения спама
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))

    # Регистрация хэндлеров
    dp.include_router(start.router)
    dp.include_router(speedtest.router)
    dp.include_router(status.router)
    dp.include_router(support.router)
    #dp.include_router(admin.router)
    dp.include_router(share.router)
    dp.include_router(start_to_connect.router)
    dp.include_router(instructions.router)
    dp.include_router(device_choice.router)
    dp.include_router(app_downloaded.router)
    dp.include_router(file_or_qr.router)
    dp.include_router(subscription.router)
    dp.include_router(user_help_request.router)
    dp.include_router(payments_handler_redis.router)
    dp.include_router(feedback.router)
    #dp.include_router(payment.router)



    # Запуск бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
    finally:
        await send_admin_log(bot, "Бот завершил работу и пошел отдыхать")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
