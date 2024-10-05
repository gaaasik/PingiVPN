from aiogram import Router, types
from aiogram.filters import Command
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
from bot.keyboards.inline import create_payment_button
from bot.utils.db import get_user_status
from datetime import datetime

router = Router()

def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown в строке.
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)
@router.message(Command("status"))
@router.message(lambda message: message.text == "Информация об аккаунте ℹ️")
async def cmd_status(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    bot = message.bot

    # Сохраняем сообщение пользователя для удаления после отправки информации
    await store_message(chat_id, message.message_id, message.text, 'user')

    # Получаем данные пользователя из базы данных
    user_data = await get_user_status(user_id)  # Получаем статус и дату регистрации
    if user_data and len(user_data) == 4:  # Проверяем, что возвращено три элемента
        registration_date, days_since_registration, user_name, subscription_status = user_data



        # Вычисляем количество дней с момента регистрации
        now = datetime.now()

        # Код для отправки сообщения с кнопкой оплаты
        if subscription_status == "waiting_pending":
            status_sub_txt = f"Бесплатные 14 дней закончились \nОжидание оплаты подписки"
            # Создаем клавиатуру с кнопкой оплаты
            reply_markup = create_payment_button()
        else:
            status_sub_txt = subscription_status
            reply_markup = None  # Без кнопок, если статус другой

        # Пример экранирования текста
        status_message = (
            f"🕒 Вы с нами уже {(str(days_since_registration))} дней! 🚀 Какой прогресс! 😎\n"
            f"Действие тарифа: {(days_since_registration)} дней \n"
            f"Имя пользователя: {(user_name)}\n"
            f"Статус подписки: *{(status_sub_txt)}*"
        )

        # Удаление старых сообщений с той же информацией
        for msg in messages_for_db:
            if msg['chat_id'] == chat_id and msg['message_text'] == status_message:
                try:
                    await bot.delete_message(chat_id, msg['message_id'])
                except Exception as e:
                    print(f"Не удалось удалить сообщение {msg['message_id']}: {e}")

        # Отправка нового сообщения с информацией об аккаунте и кнопкой оплаты, если нужно
        sent_message = await message.answer(status_message, parse_mode="Markdown", reply_markup=reply_markup)

        if sent_message and sent_message.message_id:
            # Сохраняем и регистрируем сообщение только в случае успешной отправки
            await store_message(chat_id, sent_message.message_id, status_message, 'bot')
            await register_message_type(chat_id, sent_message.message_id, 'account_status', 'bot')
        else:
            print("Ошибка: сообщение не отправлено или нет message_id")

    else:
        # Отправка сообщения, если данные не найдены
        error_message = "Ваши данные не найдены в системе."
        sent_message = await message.answer(error_message)

        if sent_message and sent_message.message_id:
            await store_message(chat_id, sent_message.message_id, error_message, 'bot')
        else:
            print("Ошибка: сообщение не отправлено или нет message_id")

    # Удаление сообщения пользователя после обработки
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя {message.message_id}: {e}")

    # Удаляем неважные сообщения
    await delete_unimportant_messages(chat_id, bot)

