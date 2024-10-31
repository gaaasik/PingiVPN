# menu_buy_vpn.py
from aiogram import Router
from aiogram.types import CallbackQuery

from models.UserCl import UserCl

# Инициализация роутера
router = Router()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery


# Создание клавиатуры для каждого статуса
def get_payment_keyboard():
    # Создаем клавиатуру с вложенным списком кнопок
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц: 199₽", callback_data="pay_subscription")]
    ])
    return keyboard

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

    # Получаем количество ключей и статус
    count_key = await us.count_key.get()
    keyboard = None
    text = ""

    if count_key == 0:
        # Если у пользователя нет ключей
        text = (
            "У вас нет ключей для оплаты.\n"
            "Создайте ключ."
        )
        keyboard = get_add_key_keyboard()

    else:
        # Получаем статус первого ключа
        status_key = await us.servers[0].status_key.get()
        key_name = await us.servers[0].email_key.get()

        if status_key == "free_key":
            # Пробный период ключа
            trial_end_date = await us.servers[0].date_key_off.get_date()  # Обрезаем до 'ГГГГ-ММ-ДД'
            text = (
                f"Ваш ключ: {key_name}\n"
                f"Его статус: *пробный период*\n"
                f"Пробный период ключа до *{trial_end_date}*\n\n"
                "Стоимость подписки на *30* дней: *199₽*"
            )
            keyboard = get_payment_keyboard()

        elif status_key == "blocked":
            # Ключ заблокирован
            text = (
                f"Ваш ключ: {key_name}\n"
                "Его статус: *заблокирован*\n\n"
                "Чтобы ключ активировался, оплатите его.\n"
                "При оплате он будет активен в течение 30 дней.\n\n"
                "Стоимость подписки на *30* дней: *199₽*"
            )
            keyboard = get_payment_keyboard()

        elif status_key == "active":
            # Ключ активен
            active_end_date = await us.servers[0].date_key_off.get_date()  # Обрезаем до 'ГГГГ-ММ-ДД'
            text = (
                f"Ваш ключ: {key_name}\n"
                f"Cтатус: *активен*\n"
                f"Ключ активен до: *{active_end_date}*\n\n"
                "При оплате вы продлите срок активного ключа еще на *30 дней*"
            )
            keyboard = get_payment_keyboard()

    # Отправка сообщения с соответствующей клавиатурой
    await callback_query.message.answer(text, reply_markup=keyboard,parse_mode="Markdown")
    await callback_query.answer()
