from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv
from aiogram.fsm.storage.memory import MemoryStorage
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())