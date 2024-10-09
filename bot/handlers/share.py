# bot/handlers/share.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os

name_bot = os.getenv('name_bot')
router = Router()



@router.message(Command("share"))
@router.message(lambda message: message.text == "Поделиться с другом!")
async def cmd_share(message: types.Message):

    chat_id = message.chat.id
    user_id = message.from_user.id
    bot = message.bot
    share_message = (
        f"Твой друг тоже заслуживает безопасный интернет! \n"
        f"\nРеферальный код для друга: {chat_id} "
        f"\n*Перешли это сообщение* и помоги ему подключиться к нашему VPN-сервису. 🌐🔒🚀"
        f"\n14 дней бесплатного доступа другу и 3 бесплатных дня тебе "


    )
    # Сохраняем сообщение пользователя для удаления после отправки информации
    await store_message(chat_id, message.message_id, message.text, 'user')

    # Генерируем реферальную ссылку
    referral_link = f"https://t.me/{name_bot}?start={user_id}"  # Замените 'YourBot' на username вашего бота

    # Создаем инлайн-кнопку с реферальной ссылкой
    share_link_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поделиться с другом", url=referral_link)]
        ]
    )

    # Удаление всех старых сообщений с тем же текстом
    for msg in messages_for_db:
        if msg['chat_id'] == chat_id and msg['message_text'] == share_message:
            try:
                await bot.delete_message(chat_id, msg['message_id'])
            except Exception as e:
                print(f"Не удалось удалить сообщение {msg['message_id']}: {e}")

    # Отправка нового сообщения с кнопкой
    sent_message = await message.answer(share_message, reply_markup=share_link_button, parse_mode="Markdown")

    # Регистрируем тип сообщения для маппинга, чтобы можно было его удалять
    if sent_message:
        await store_message(chat_id, sent_message.message_id, share_message, 'bot')
        await register_message_type(chat_id, sent_message.message_id, 'share_friends','bot')  # Оставляем await, т.к. функция асинхронная
    else:
        print("Ошибка отправки сообщения: message.answer вернул None")

    # Удаляем неважные сообщения
    await delete_unimportant_messages(chat_id, bot)

    # Удаление сообщения пользователя после обработки
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя {message.message_id}: {e}")

# Обработчик нажатия на инлайн-кнопку "share_friend"
@router.callback_query(lambda callback_query: callback_query.data == "share_friend")
async def cmd_share_callback(callback_query: types.CallbackQuery):

    user_id = callback_query.from_user.id
    bot = callback_query.bot
    chat_id = callback_query.from_user.id  # Получаем chat_id через from_user.id для callback_query
    share_message = (
        f"Твой друг тоже заслуживает безопасный интернет! \n"
        f"\nРеферальный код для друга: {chat_id} "
        f"\nПерешли это сообщение и помоги ему подключиться к нашему VPN-сервису. 🌐🔒🚀"
        f"\n14 дней бесплатного доступа другу и 3 бесплатных дня тебе "

    )
    # Генерация реферальной ссылки
    referral_link = f"https://t.me/{name_bot}?start={user_id}"

    # Создаем инлайн-кнопку с реферальной ссылкой
    share_link_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поделиться с другом", url=referral_link)]
        ]
    )

    # Отправляем сообщение с кнопкой в ответ на нажатие инлайн-кнопки
    sent_message = await bot.send_message(chat_id, share_message, reply_markup=share_link_button, parse_mode="Markdown")

    # Регистрируем сообщение для удаления в будущем
    if sent_message:
        await store_message(chat_id, sent_message.message_id, share_message, 'bot')
        await register_message_type(chat_id, sent_message.message_id, 'share_friends', 'bot')

    # Закрываем уведомление о нажатии кнопки
    await callback_query.answer()