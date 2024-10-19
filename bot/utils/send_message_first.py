from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from bot.database.db import get_user_registration_date_and_username


async def send_messages_to_chats(bot: Bot, chat_ids, message_text, reply_markup):
    await bot.send_message(456717505, message_text, reply_markup=reply_markup, parse_mode="Markdown")

    for chat_data in chat_ids:
        chat_id = chat_data[0]  # Извлекаем только chat_id из кортежа
        user_status = await get_user_registration_date_and_username(chat_id)

        if user_status == "waiting_pending":
            print(f"Пользователь с chat_id {chat_id} уже получил сообщение, но сейчас сообщение  будет отправлено.")
            continue  # Пропускаем пользователя, если статус 'waiting_pending'

        try:
            # Отправляем сообщение пользователю
            #await bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup, parse_mode="Markdown")

            # Обновляем статус пользователя на 'waiting_pending'
           #await update_user_status(chat_id, 'waiting_pending')
            print(f"Message successfully sent to chat {chat_id}")

        except TelegramForbiddenError:
            # Логируем или обрабатываем случай, когда бот заблокирован пользователем
            print(f"Bot was blocked by user {chat_id}, skipping.")
        except Exception as e:
            # Логируем другие возможные ошибки
            print(f"An error occurred while sending message to {chat_id}: {e}")