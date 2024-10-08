import asyncio
import logging
import os
from pathlib import Path
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from app import initialize_db, add_column_to_payments, ensure_payments_table_exists
from bot.handlers.admin import send_admin_log
from bot.keyboards.inline import create_feedback_keyboard
#from bot.payments2.payments_db import init_payment_db
from bot.utils.add_ip_adress import update_user_ip_info
from bot.utils.db import who_have_expired_trial, add_user
from bot.handlers import start, status, support, admin, share, start_to_connect, instructions, \
    device_choice, app_downloaded, file_or_qr, subscription, speedtest, user_help_request, feedback


from bot.payments2 import payments_handler



from bot.utils.cache import cache_media
from bot.utils.check_status import check_db, ADMIN_CHAT_ID, notify_users_with_free_status
from bot.utils.logger import setup_logger
from bot.utils.db import init_db,database_path_local
from bot.midlewares.throttling import ThrottlingMiddleware
from bot_instance import BOT_TOKEN, dp, bot

#from bot_instance import bot, dp, BOT_TOKEN

# Загружаем переменные окружения из файла .env
load_dotenv()


# Глобальная переменная для хранения экземпляра бота

#bot = None



PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
video_path = os.getenv("video_path")
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')
database_path_local = os.getenv('database_path_local')

############################################################################################################

# BOT_TOKEN = os.getenv('BOT_TOKEN')
# bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
# dp = Dispatcher(storage=MemoryStorage())

############################################################################################


async def on_startup():
    """Кэширование изображений при старте"""
    image_path = os.path.join(PATH_TO_IMAGES, "Hello.png")
    print('закешировали приветственное фото')
    await cache_media(image_path, video_path)


# Функция, которая выполняется каждые 10 секунд
async def periodic_task(bot: Bot):
    # Ждем 10 секунд после старта бота
    await asyncio.sleep(43200)
    while True:
        await send_admin_log(bot, "Прошло 43200 секунд с запуска бота.")
        await check_db(bot)
        # Пример асинхронного вызова
       # await notify_users_with_free_status(bot)
        await asyncio.sleep(43200)
async def main():
    #global bot
    await on_startup()
    initialize_db()
    # Пример использования:
    #add_column_to_payments("new_column_name")
    # Вызов функции для проверки и создания таблицы при запуске приложения
    ensure_payments_table_exists()
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
    ###############################################################################
    #await init_payment_db()
    ###############################################################################
    result = await add_user(111224422, "test_user")
    print(result)
    # Запускаем асинхронную задачу для периодической отправки сообщений админу
    asyncio.create_task(periodic_task(bot))

    #await update_user_ip_info(bot, database_path_local, REGISTERED_USERS_DIR)


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
    dp.include_router(payments_handler.router)
    dp.include_router(feedback.router)
    #dp.include_router(payment.router)
    # Запуск бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(e)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
