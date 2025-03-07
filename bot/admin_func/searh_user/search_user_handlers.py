import os
import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.admin_func.keyboards import get_search_user_keyboard, get_user_service_keyboard
from bot.admin_func.states import AdminStates
from bot.admin_func.searh_user.utils import user_to_json, format_user_data
from models.UserCl import UserCl

router = Router()
DB_PATH = os.getenv('database_path_local')


# 📌 Меню поиска пользователя
@router.callback_query(F.data == "search_user")
async def search_user_menu(callback: CallbackQuery, state: FSMContext):
    """Меню выбора способа поиска"""
    keyboard = await get_search_user_keyboard()
    await callback.message.edit_text("🔍 Выберите способ поиска пользователя:", reply_markup=keyboard)
    await callback.answer()



# 📌 Запрос на ввод Chat ID (добавлена кнопка "🔙 Назад")
@router.callback_query(F.data == "search_by_chat_id")
async def search_by_chat_id(callback: CallbackQuery, state: FSMContext):
    """Просим ввести Chat ID с возможностью вернуться назад"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
    ])

    await callback.message.edit_text("🔢 Введите Chat ID пользователя:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_chat_id)
    await callback.answer()


# 📌 Обработка ввода Chat ID (добавлена кнопка "🔙 Назад" и возврат при ошибке)
@router.message(AdminStates.waiting_for_chat_id)
async def handle_chat_id_input(message: types.Message, state: FSMContext):
    """Обрабатываем ввод Chat ID"""
    try:
        chat_id = message.text.strip()
        if not chat_id.isdigit():
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
            ])
            await message.answer("⚠️ Chat ID должен быть числом. Попробуйте снова.", reply_markup=keyboard)
            return

        user = await UserCl.load_user(int(chat_id))  # Загружаем пользователя
        if not user:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
            ])
            await message.answer("❌ Пользователь не найден.", reply_markup=keyboard)
            return

        # Сохраняем найденного пользователя
        await state.update_data(current_user=user)

        # Получаем данные пользователя
        user_json = await user_to_json(user, DB_PATH)
        formatted_data = await format_user_data(user_json)

        # Кнопки действий
        keyboard = await get_user_service_keyboard()

        # Отправляем новое сообщение и сохраняем его ID
        sent_message = await message.answer(
            f"✅ Найден пользователь:\n{formatted_data}\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.update_data(last_message_id=sent_message.message_id)

        # Меняем состояние
        await state.set_state(AdminStates.waiting_for_action)

    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer("❌ Произошла ошибка при обработке запроса.")