# bot/handlers/admin.py
from aiogram import Router, types
router = Router()

#
# @router.message(lambda message: message.text == "Список пользователей")
# async def cmd_list_users(message: types.Message):
#     users = await get_all_users()
#
#     if users:
#         user_list = "\n".join([f"ID: {user[0]}, Телеграм ID: {user[1]}, Номер телефона: {user[2]}" for user in users])
#         await message.answer(f"Список пользователей:\n{user_list}")
#     else:
#         await message.answer("Нет зарегистрированных пользователей.")
#
#
#
# @router.message(lambda message: message.text and message.text.startswith("Заблокировать"))
# async def block_user_handler(message: types.Message):
#     # Ваш код для блокировки пользователя
#     user_to_block = message.text.split()[1]  # Пример получения идентификатора пользователя
#     # Логика блокировки пользователя
#     await message.answer(f"Пользователь {user_to_block} был заблокирован.")
