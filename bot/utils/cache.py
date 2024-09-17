# bot/utils/cache.py
import os
from aiogram.types import FSInputFile

from bot.keyboards.reply import reply_keyboard

cached_photo = None
cached_video = None
async def cache_media(image_path: str, video_path: str):
    global cached_photo, cached_video

    # Кэшируем фото
    if os.path.exists(image_path):
        cached_photo = FSInputFile(image_path)
        print("Изображение закешировано.")
    else:
        print("Изображение не найдено, проверьте путь.")

    # Кэшируем видео
    if os.path.exists(video_path):
        cached_video = FSInputFile(video_path)
        print("Видео закешировано.")
    else:
        print("Видео не найдено, проверьте путь.")

async def send_cached_photo(message):
    global cached_photo

    if cached_photo:
        await message.answer_photo(photo=cached_photo,reply_markup=reply_keyboard)
    else:
        await message.answer("Изображение не закешировано, проверьте настройки.")

