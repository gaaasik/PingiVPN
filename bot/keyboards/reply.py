# bot/keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Кнопки для основного меню после регистрации

reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Показать QR и файл"),
         KeyboardButton(text="Информация об аккаунте ℹ️")],
        [#KeyboardButton(text="Удалить конфигурацию ❌"),
         #KeyboardButton(text="Удалить регистрацию")
        KeyboardButton(text="Поделиться с другом!")
        ],

        [KeyboardButton(text="Задать вопрос 🙋‍♂️")]
    ],
    resize_keyboard=True
)
# # Клавиатура командных кнопок
# command_keyboard = ReplyKeyboardMarkup(
#     keyboard=[
#         [KeyboardButton(text="Начать !!!")],
#         [KeyboardButton(text="Добавить конфигурацию 🚀✅"), KeyboardButton(text="Информация об аккаунте ℹ️")],
#         [KeyboardButton(text="Удалить конфигурацию ❌"), KeyboardButton(text="Удалить регистрацию")],
#         [KeyboardButton(text="Задать вопрос 🙋‍♂️")]
#     ],
#     resize_keyboard=True
# )

