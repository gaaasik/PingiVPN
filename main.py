# main.py
import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from bot.handlers import start, status, support, admin, share, start_to_connect, instructions, \
    device_choice, app_downloaded, file_or_qr, subscription, speedtest, user_help_request
from bot.utils.cache import cache_media
from bot.utils.logger import setup_logger
from bot.utils.db import init_db, drop_table, add_device_column

from bot.midlewares.throttling import ThrottlingMiddleware
import os
# Загружаем переменные окружения из файла .env

load_dotenv()  # Указываем путь к .env файлу
PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
video_path = os.getenv("video_path")
async def on_startup():
    # Кэшируем изображение при старте
    image_path = os.path.join(PATH_TO_IMAGES, "Hello.png")
    print('закешировали приветственное фото'
          '')
    # Кэшируем фото и видео
    await cache_media(image_path, video_path)
async def main():
    await on_startup()
    # Читаем токен бота из переменной окружения
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    if BOT_TOKEN:
        print(f"Токен успешно загружен: {BOT_TOKEN}")
    else:
        print("Ошибка: Токен не найден в .env файле!")
    # Настраиваем логирование
    setup_logger("logs/bot.log")
    # Указываем путь к базе данных
    db_path = Path(os.getenv('database_path_local'))

    # Проверяем, что файл существует
    if db_path.exists():
        print(f"Путь к базе данных: {db_path}")
    else:
        print("Файл базы данных не найден!")

   ### await drop_table('vpn_bot.db', 'users')


    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    # Инициализация базы данных SQLite
    database = await init_db(db_path)
    # Промежуточное ПО для предотвращения спама
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))

    # Регистрация хэндлеров
    dp.include_router(start.router)
    dp.include_router(speedtest.router)
    dp.include_router(status.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(share.router)
    dp.include_router(start_to_connect.router)
    dp.include_router(instructions.router)
    dp.include_router(device_choice.router)
    dp.include_router(app_downloaded.router)
    dp.include_router(file_or_qr.router)
    dp.include_router(subscription.router)
    dp.include_router(user_help_request.router)
    # Запуск бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(e)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
