# # bot/handlers/unknown_message.py
#
# from aiogram import Router, types
# from bot.handlers.cleanup import store_message, delete_unimportant_messages
# from data.text_messages import unknow_message
#
# router = Router()
#
# @router.message()
# async def handle_unknown_message(message: types.Message):
#     """
#     Обрабатывает все сообщения, которые не были распознаны другими обработчиками.
#     """
#     chat_id = message.chat.id
#     bot = message.bot
#
#     # Сохраняем сообщение пользователя
#     await store_message(chat_id, message.message_id, message.text, 'user')
#
#     # Ответ пользователю
#     response_message = await message.answer(unknow_message)
#
#     # Сохраняем ответ бота
#     await store_message(chat_id, response_message.message_id, response_message.text, 'bot')
#
#     # Удаляем неважные сообщения
#     await delete_unimportant_messages(chat_id, bot)
