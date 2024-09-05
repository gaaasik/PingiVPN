# # bot/handlers/commands.py
# from aiogram import Router, types
# from aiogram.filters import Command
#
# from bot.handlers.cleanup import store_message
# from bot.utils.db import add_connection, remove_connection, get_active_connections_count, get_user_status, delete_user, \
#     get_user_by_telegram_id
#
# router = Router()
#
# from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
#
# @router.message(Command("status"))
# async def cmd_status(message: types.Message):
#     await store_message(message.chat.id, message.message_id)
#     user_id = message.from_user.id
#     user_status = await get_user_status(user_id)
#
#     if user_status:
#         registration_date, user_name = user_status
#         await message.answer(
#             f"Дата регистрации: {registration_date}\nИмя пользователя: {user_name}"
#         )
#         await store_message(message.chat.id, message.message_id)
#     else:
#         await message.answer("Вы не зарегистрированы. Пожалуйста, используйте /start, чтобы зарегистрироваться.")
#         await store_message(message.chat.id, message.message_id)
#
#
#
#
#
#
