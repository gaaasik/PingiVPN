# bot/keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Кнопки для основного меню после регистрации

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Подключиться 🚀"),
            KeyboardButton(text="Информация об аккаунте ℹ️")
        ],
        [
            KeyboardButton(text="Поделиться с другом!")
        ],
        [(
            KeyboardButton(text="Тарифы \n(в разработке)")
        ),
            (
            KeyboardButton(text="Проверить скорость")
        )],
        [
            KeyboardButton(text="Задать вопрос 🙋‍♂️")
        ]
    ],
    resize_keyboard=True
)
