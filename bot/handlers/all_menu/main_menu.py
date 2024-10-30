from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os
from models.UserCl import UserCl
from bot.keyboards.inline import main_menu_inline_keyboard, device_choice_keyboard

router = Router()

# Функция для отображения основного меню
async def show_main_menu(chat_id: int, bot: Bot, status: str,  days_since_registration: int):
    # Получаем данные о пользователе по chat_id
    user = await bot.get_chat(chat_id)
    user_name = f"{user.first_name} {user.last_name or ''}".strip()

    # Формирование текста главного меню
    text = (
        f"Привет {user_name}! 🕶\n\n"
        "PingiVPN - быстрый и безопасный доступ к свободному интернету без ограничений\n\n"
        "📱 Доступ к любым социальным сетям\n"
        "🛡 Анонимность\n"
        "📶 Устойчивость к блокировкам\n"
        "🚀 Высокая скорость\n"
        "💻 Поддержка любых устройств\n\n"
        f"🔑 Статус: {status}\n"
        f"🕓 Вы с нами уже {days_since_registration} дней! 🥳\n"
    )



    # Отправка сообщения с меню
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_inline_keyboard(),parse_mode="Markdown")

# Обработчики для кнопок главного меню







# Универсальный обработчик для главного меню
# Универсальный обработчик для главного меню
@router.message(F.text == "Главное меню")
@router.message(Command(commands=["menu"]))
@router.callback_query(F.data == "main_menu")
async def handle_main_menu(event: types.Message | types.CallbackQuery):
    # Проверяем тип события (Message или CallbackQuery)
    if isinstance(event, types.CallbackQuery):
        chat_id = event.message.chat.id
        bot = event.bot
        await event.answer()  # Закрыть CallbackQuery, чтобы Telegram не показывал часы загрузки
    else:
        chat_id = event.chat.id
        bot = event.bot

    # Пример данных, которые могут быть получены из базы данных
    status = ":актуальный статус:"  # Пример статуса
    days_since_registration = 100

    # Отображение главного меню
    await show_main_menu(chat_id, bot, status, days_since_registration)