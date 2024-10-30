from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()




# Кнопка для перехода на канал и кнопка для проверки подписки
def subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти на канал", url="https://t.me/pingi_hub")],
        [InlineKeyboardButton(text="Я подписался", callback_data="connect_vpn")]
    ])
    return keyboard