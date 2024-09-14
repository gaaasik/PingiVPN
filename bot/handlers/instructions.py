# bot/handlers/instructions.py
import os
import re

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from dotenv import load_dotenv

from data.text_messages import detailed_instructions_message

router = Router()

load_dotenv()
@router.callback_query(lambda c: c.data == 'detailed_instruction')
async def send_detailed_instructions(callback_query: types.CallbackQuery):
    """
    Обработчик для inline-кнопки "📜 Подробная инструкция".
    Отправляет пользователю видео и текст с подробной инструкцией.
    """
    # Укажите правильный путь к вашему видеофайлу
    video_path = os.getenv('video_path')

    # Экранируем специальные символы в тексте инструкции
    escaped_instructions_message = re.sub(r'([*_`\[])', r'\\\1', detailed_instructions_message)

    # Отправляем текст с подробной инструкцией
    await callback_query.message.answer(
        escaped_instructions_message,
        parse_mode="Markdown"
    )
    # Проверяем, существует ли файл с видео
    if os.path.exists(video_path):
        video_file = FSInputFile(video_path)
        await callback_query.message.answer_video(video=video_file)




    await callback_query.answer()  # Уведомляем Telegram о получении callback запроса