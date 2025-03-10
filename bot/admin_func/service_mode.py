import os
import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.admin_func.keyboards import get_service_mode_keyboard
from bot.admin_func.states import AdminStates
from bot.handlers.admin import ADMIN_CHAT_IDS

router = Router()
DB_PATH = os.getenv('database_path_local')

@router.message(F.text == "Режим обслуживания")
async def start_user_service_mode(message: types.Message, state: FSMContext):
    """Меню режима обслуживания (удаляет старое сообщение, если есть)"""
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return

    # Проверяем, есть ли уже активное сообщение
    data = await state.get_data()
    last_message_id = data.get("last_message_id")

    # Если есть предыдущее сообщение – удаляем его
    if last_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_message_id)
        except Exception:
            pass  # Игнорируем ошибки удаления

    keyboard = await get_service_mode_keyboard()

    sent_message = await message.answer("🔧 Вы в режиме обслуживания. Выберите действие:", reply_markup=keyboard)

    # Сохраняем ID нового сообщения
    await state.update_data(last_message_id=sent_message.message_id)
    await state.set_state(AdminStates.waiting_for_search_method)


# 📌 Обработка нажатия "Назад"
@router.callback_query(F.data == "cancel_service")
async def handle_cancel_service(callback: CallbackQuery, state: FSMContext):
    """Возвращаем в главное меню"""
    await state.clear()

    keyboard = await get_service_mode_keyboard()

    await callback.message.edit_text("🔧 Вы в режиме обслуживания. Выберите действие:", reply_markup=keyboard)
    await callback.answer()


# 📌 Обработка выхода из режима обслуживания
@router.callback_query(F.data == "exit_service_mode")
async def exit_service_mode(callback: CallbackQuery, state: FSMContext):
    """Полностью выходим из режима обслуживания, сбрасываем состояние и отправляем главное меню"""
    await state.clear()

    # Отправляем главное меню (можно заменить на своё)
    main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

    await callback.message.edit_text("🏠 Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
    await callback.answer()



# import os

# import logging
#
# from aiogram import Router, types, F
# from aiogram.fsm.context import FSMContext
# from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# from bot.admin_func.keyboards import get_search_user_keyboard, get_user_service_keyboard, get_service_mode_keyboard
# from bot.admin_func.states import AdminStates
# from bot.admin_func.utils import user_to_json, format_user_data
# from bot.handlers.admin import ADMIN_CHAT_IDS
# from models.UserCl import UserCl
#
# router = Router()
# DB_PATH = os.getenv('database_path_local')
#
# @router.message(F.text == "Режим обслуживания")
# async def start_user_service_mode(message: types.Message, state: FSMContext):
#     """Меню режима обслуживания (удаляет старое сообщение, если есть)"""
#     if message.from_user.id not in ADMIN_CHAT_IDS:
#         await message.answer("❌ У вас нет прав для использования этой команды.")
#         return
#
#     # Проверяем, есть ли уже активное сообщение
#     data = await state.get_data()
#     last_message_id = data.get("last_message_id")
#
#     # Если есть предыдущее сообщение – удаляем его
#     if last_message_id:
#         try:
#             await message.bot.delete_message(chat_id=message.chat.id, message_id=last_message_id)
#         except Exception:
#             pass  # Игнорируем ошибки удаления
#
#     keyboard = await get_service_mode_keyboard()
#
#     sent_message = await message.answer("🔧 Вы в режиме обслуживания. Выберите действие:", reply_markup=keyboard)
#
#     # Сохраняем ID нового сообщения
#     await state.update_data(last_message_id=sent_message.message_id)
#     await state.set_state(AdminStates.waiting_for_search_method)
#
# # 📌 Меню поиска пользователя
# @router.callback_query(F.data == "search_user")
# async def search_user_menu(callback: CallbackQuery, state: FSMContext):
#     """Меню выбора способа поиска"""
#     keyboard =await get_search_user_keyboard()
#
#     await callback.message.edit_text("🔍 Выберите способ поиска пользователя:", reply_markup=keyboard)
#     await callback.answer()
#
#
# # 📌 Запрос на ввод Chat ID
# @router.callback_query(F.data == "search_by_chat_id")
# async def search_by_chat_id(callback: CallbackQuery, state: FSMContext):
#     """Просим ввести Chat ID"""
#     await callback.message.edit_text("🔢 Введите Chat ID пользователя:")
#     await state.set_state(AdminStates.waiting_for_chat_id)
#     await callback.answer()
#
#
# # 📌 Обработка ввода Chat ID (удаляем предыдущее сообщение)
# @router.message(AdminStates.waiting_for_chat_id)
# async def handle_chat_id_input(message: types.Message, state: FSMContext):
#     """Обрабатываем ввод Chat ID"""
#     try:
#         chat_id = message.text.strip()
#         if not chat_id.isdigit():
#             await message.answer("⚠️ Chat ID должен быть числом. Попробуйте снова.")
#             return
#
#         user = await UserCl.load_user(int(chat_id))  # Загружаем пользователя
#         if not user:
#             await message.answer("❌ Пользователь не найден.")
#             return
#
#         # Удаляем предыдущее сообщение, если оно было
#         data = await state.get_data()
#         last_message_id = data.get("last_message_id")
#         if last_message_id:
#             try:
#                 await message.bot.delete_message(chat_id=message.chat.id, message_id=last_message_id)
#             except Exception:
#                 pass  # Игнорируем ошибки удаления
#
#         # Сохраняем найденного пользователя
#         await state.update_data(current_user=user)
#
#         # Получаем данные пользователя
#         user_json = await user_to_json(user, DB_PATH)
#         formatted_data = await format_user_data(user_json)
#
#         # Кнопки действий
#         keyboard = await get_user_service_keyboard()
#
#         # Отправляем новое сообщение и сохраняем его ID
#         sent_message = await message.answer(
#             f"✅ Найден пользователь:\n{formatted_data}\n\nВыберите действие:",
#             parse_mode="HTML",
#             reply_markup=keyboard
#         )
#         await state.update_data(last_message_id=sent_message.message_id)
#
#         # Меняем состояние
#         await state.set_state(AdminStates.waiting_for_action)
#
#     except Exception as e:
#         logging.error(f"Ошибка при поиске пользователя: {e}")
#         await message.answer("❌ Произошла ошибка при обработке запроса.")
#
#
# # 📌 Обработка нажатия "Назад"
# @router.callback_query(F.data == "cancel_service")
# async def handle_cancel_service(callback: CallbackQuery, state: FSMContext):
#     """Возвращаем в главное меню"""
#     await state.clear()
#
#     keyboard = await get_service_mode_keyboard()
#
#     await callback.message.edit_text("🔧 Вы в режиме обслуживания. Выберите действие:", reply_markup=keyboard)
#     await callback.answer()
#
#     # 📌 Обработка нажатия "❌ Выйти из режима обслуживания"
#
#
# @router.callback_query(F.data == "exit_service_mode")
# async def exit_service_mode(callback: CallbackQuery, state: FSMContext):
#     """Полностью выходим из режима обслуживания, сбрасываем состояние и отправляем главное меню"""
#     await state.clear()
#
#     # Отправляем главное меню (можно заменить на своё)
#     main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
#     ])
#
#     await callback.message.edit_text("🏠 Вы вернулись в главное меню.", reply_markup=main_menu_keyboard)
#     await callback.answer()