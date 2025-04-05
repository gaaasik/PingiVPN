# menu_buy_vpn.py
import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.handlers.admin import ADMIN_CHAT_IDS, send_admin_log
from bot.handlers.all_menu.main_menu import get_user_status_text
from models.UserCl import UserCl
from models.referral_class.ReferralCL import ReferralCl

# Инициализация роутера
router = Router()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery


# Создание клавиатуры для каждого статуса

# Словарь тарифов
TARIFFS = {
    "1": {"months": 1, "amount": "199.00", "label": "1 месяц"},
    "3": {"months": 3, "amount": "549.00", "label": "3 месяца"},
    "6": {"months": 6, "amount": "1049.00", "label": "6 месяцев"},
}

def get_payment_keyboard():
    buttons = []

    for tariff_id, tariff in TARIFFS.items():
        text = f"📦 {tariff['label']} — {tariff['amount']}₽"
        callback_data = f"payment_plan_{tariff_id}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_add_key_keyboard():
    # Создаем клавиатуру с вложенным списком кнопок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить ключ", callback_data="connect_vpn")]
    ])
    return keyboard

@router.callback_query(lambda c: c.data == "buy_vpn")
async def handle_buy_vpn(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    us = await UserCl.load_user(chat_id)
    # # Проверка на администратора
    # if not (int(chat_id) in ADMIN_CHAT_IDS):
    #     # Отправка сообщения для неадминистратора
    #     await callback_query.message.answer(
    #         f"Оплата скоро будет доступна, если у вас проблемы с подключением напишите нам @pingi_help"
    #
    #     )
    #     await callback_query.answer()
    #     return  # Завершаем выполнение функции


    # Получаем количество ключей и статус
    count_key = await us.count_key.get()
    keyboard = None
    text = ""
    active_server = us.active_server
    if count_key == 0 or not active_server:
        # Если у пользователя нет ключей
        text = (
            "У вас нет ключей для оплаты.\n"
            "Создайте ключ."
        )
        keyboard = get_add_key_keyboard()

    else:
        # Получаем статус первого ключа
        if us.active_server:
            status_key = await us.active_server.status_key.get()
            key_name = await us.active_server.name_key.get()
            date_key_off = await us.active_server.date_key_off.get_date()
            enabled = await us.active_server.enable.get()
            has_paid_key = await us.active_server.has_paid_key.get()
            if enabled == True and has_paid_key == 0:
                 # Обрезаем до 'ГГГГ-ММ-ДД'
                text = (
                    f"Ваш ключ: {key_name}\n"
                    f"Его статус: <b>пробный период</b>\n"
                    f"Пробный период ключа до <b>{date_key_off}</b>\n\n"
                    "Стоимость подписки на <b>30</b> дней: <b>199₽</b>"
                )
                keyboard = get_payment_keyboard()

            elif enabled == False:
                # Ключ заблокирован
                text = (
                    f"Ваш ключ: {key_name}\n"
                    "Его статус: <b>заблокирован</b>\n\n"
                    "Чтобы ключ активировался, оплатите его.\n"
                    "При оплате он будет активен в течение 30 дней.\n\n"
                    "Стоимость подписки на <b>30</b> дней: <b>199₽</b>"
                )
                keyboard = get_payment_keyboard()

            elif enabled == True and has_paid_key > 0:
                # Ключ активен
                text = (
                    f"Ваш ключ: {key_name}\n"
                    f"Cтатус: {await get_user_status_text(us)}\n"
                    f"Ключ активен до: <b>{date_key_off}</b>\n\n"
                    "При оплате вы получите доступ на *30 дней* "
                )
                keyboard = get_payment_keyboard()

    # Отправка сообщения с соответствующей клавиатурой
    await callback_query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await send_admin_log(callback_query.bot, f"Пользователь {chat_id} нажал первую кнопку оплатить")

    # #ТЕСТ Проверяем реферальную систему и начисляем бонус пригласившему
    # try:
    #     await ReferralCl.add_referral_bonus_after_pay(chat_id, callback_query.bot)
    # except Exception as e:
    #     logging.error(f"❌ Ошибка при начислении бонуса за оплату {chat_id}: {e}")
    # #ТЕСТ
    await callback_query.answer()
