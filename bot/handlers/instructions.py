# bot/handlers/instructions.py
import os
import re

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, CallbackQuery
from dotenv import load_dotenv

from data.text_messages import detailed_instructions_message

router = Router()

load_dotenv()