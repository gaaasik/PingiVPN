# bot/handlers/menu_share.py
import os

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message, CallbackQuery

router = Router()
name_bot = os.getenv('name_bot')


# Текст сообщения для реферальной программы
def generate_referral_text(invite_count: int):
    return (
        "🎉 *Приглашайте друзей и получайте бонусные дни!*\n\n"
        "1. Нажмите *Поделится* \n\n"
        "2. *Перешлите сообщение другу* или *поделитесь ссылкой*\n\n"
        "- Друг получит *7 дней* бесплатного доступа\n"
        "- Вы получите *2 бонусных дня* за каждого друга, подключившегося *по вашей ссылке*\n"
        "- Если друг оформит подписку, вам начисляется *10 бонусных дней*\n\n"
        f"Количество приглашенных: {invite_count}"
    )


# Клавиатура с кнопкой для реферальной ссылки
# Клавиатура с кнопками "Показать реферальную ссылку" и "Главное меню"
def referral_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Поделиться", callback_data="show_referral_link")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )


# Универсальный обработчик для команды "/share" и кнопки "Пригласить"
@router.message(Command("share"))
@router.callback_query(F.data == "share")
async def handle_share(event: Message | CallbackQuery, bot: Bot):
    chat_id = event.from_user.id
    referral_code = chat_id
    referral_link = f"https://t.me/{name_bot}?start={referral_code}"

    # Формируем сообщение о реферальной программе
    share_message = generate_referral_text(-1)
    share_keyboard = referral_menu_keyboard()

    # Отправляем сообщение в зависимости от типа события
    if isinstance(event, Message):
        await event.answer(share_message, reply_markup=share_keyboard, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(share_message, reply_markup=share_keyboard, parse_mode="Markdown",
                                      disable_web_page_preview=True)
        await event.answer()


# Обработчик для кнопки "Показать реферальную ссылку"
@router.callback_query(F.data == "show_referral_link")
async def show_referral_link(callback_query: CallbackQuery, bot: Bot):
    chat_id = callback_query.from_user.id
    name_bot = "PingiVPN_bot"
    # Формируем реферальную ссылку
    referral_link = f"https://t.me/{name_bot}?start={chat_id}"

    # Текст сообщения с реферальной ссылкой
    referral_link_text = (
        f"🚀 *Разблокируйте любимые сайты и приложения!*\n\n"
        f"Ваш друг *рекомендует* наш VPN для доступа к контенту без ограничений.\n"
        f"👉 Ваша ссылка на бота:\n\n"
        f"🔗 [Перейти к боту]({referral_link})\n\n"
        f"Для копирования:\n"
        f"```{referral_link}```"  # Отформатированная ссылка для копирования
    )

    # Кнопка для получения доступа
    referral_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Получить бесплатный VPN", url=referral_link)]
        ]
    )

    # Отправляем сообщение с реферальной ссылкой и кнопкой
    await callback_query.message.answer(referral_link_text, reply_markup=referral_button, parse_mode="Markdown")
    await callback_query.answer()
