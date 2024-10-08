import asyncio

from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv
from aiogram.fsm.storage.memory import MemoryStorage
from redis import asyncio as aioredis

from flask_app.bot_processor import listen_to_redis_queue

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
try:
    # Запуск в основном цикле событий
    asyncio.run(listen_to_redis_queue(bot))
except Exception as e:
    print(f"Ошибка при запуске прослушивания очереди Redis: {e}")