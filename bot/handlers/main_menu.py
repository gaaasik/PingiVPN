from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os

from bot.keyboards.inline import main_menu_inline_keyboard

router = Router()

# Функция для отображения основного меню
async def show_main_menu(chat_id: int, bot: Bot, status: str, payment_date: str, trial_date: str, days_since_registration: int):
    # Формирование текста главного меню
    text = (
        f"Привет, {chat_id} 🕶\n\n"
        "PingiVPN - быстрый и безопасный доступ к свободному интернету без ограничений\n\n"
        "📱 Доступ к любым социальным сетям\n"
        "🛡 Анонимность\n"
        "📶 Устойчивость к блокировкам\n"
        "🚀 Высокая скорость\n"
        "💻 ```\n Поддержка любых устройств\n```\n\n"
        f"🔑 Статус: {status}\n"
        f"📅 *ключ* оплачен до {payment_date}\n"
        f"\\ пробный период до {trial_date}\n\n"
        f"🕓 Вы с нами уже {days_since_registration} дней! 🥳\n"
    )



    # Отправка сообщения с меню
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_inline_keyboard(),parse_mode="Markdown")

# Обработчики для кнопок главного меню
@router.callback_query(lambda c: c.data == "buy_vpn")
async def handle_buy_vpn(callback_query: CallbackQuery):
    await callback_query.answer("Купить VPN: функционал пока не реализован.")

@router.callback_query(lambda c: c.data == "my_keys")
async def handle_my_keys(callback_query: CallbackQuery):
    await callback_query.answer("Мои ключи: функционал пока не реализован.")

@router.callback_query(lambda c: c.data == "help")
async def handle_help(callback_query: CallbackQuery):
    await callback_query.answer("Помощь: функционал пока не реализован.")

@router.callback_query(lambda c: c.data == "share")
async def handle_share(callback_query: CallbackQuery):
    await callback_query.answer("Пригласить: функционал пока не реализован.")

@router.callback_query(lambda c: c.data == "about_vpn")
async def handle_about_vpn(callback_query: CallbackQuery):
    await callback_query.answer("Всё о PingiVPN: функционал пока не реализован.")

# Обработчик для команды, вызывающий главное меню
@router.message(lambda message: message.text == "Главное меню")
async def handle_main_menu(message: types.Message):

    chat_id = message.chat.id
    bot = message.bot
    # Пример данных, которые могут быть получены из базы данных
    status = "ключ оплачен до 12.34.5025"  # Пример статуса
    payment_date = ("```vless://90b5d83f-e3c6-4381-91c4-7d624dc1c490@194.87.208.18:443?type=tcp&security=reality&pbk"
                    "=kX9Di-f2fMnJjRxx2rMsy6_Pe5gXyRO4S1NrZw8Dcyk&fp=chrome&sni=yahoo.com&sid=9c&spx=%2F&flow=xtls"
                    "-rprx-vision#Vless-vless_5_Netherlands```")
    trial_date = "12.34.5025"
    days_since_registration = 100

    # Отображение главного меню
    await show_main_menu(chat_id, message.bot, status, payment_date, trial_date, days_since_registration)
