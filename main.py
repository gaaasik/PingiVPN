# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import start, status, support, admin, share,show_config,instructions,unknown_message
from bot.utils.logger import setup_logger
from bot.utils.db import init_db, drop_table
from bot.midlewares.throttling import ThrottlingMiddleware


import os

async def main():
    # Токен бота напрямую в коде
    BOT_TOKEN = '7036736465:AAEOlcvkYEp3MrEaS1Md0iR8Xilgti6cFuU'  # Замените 'your_bot_token_here' на реальный токен вашего бота

    # Настраиваем логирование
    setup_logger("logs/bot.log")
    db_path = os.path.abspath('vpn_bot.db')


   # await drop_table('vpn_bot.db', 'users')



    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    # Инициализация базы данных SQLite
    database = await init_db(db_path)
    # Промежуточное ПО для предотвращения спама
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))

    # Регистрация хэндлеров
    dp.include_router(start.router)
    #dp.include_router(registration.router)
    dp.include_router(status.router)
    #dp.include_router(unknown_message.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(share.router)
    dp.include_router(show_config.router)
    dp.include_router(instructions.router)
#    dp.include_router(clear.router)
    # Запуск бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(e)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
