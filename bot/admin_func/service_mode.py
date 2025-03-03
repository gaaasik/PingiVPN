import os

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from bot.admin_func.keyboards import get_search_user_keyboard, get_user_service_keyboard
from bot.admin_func.states import AdminStates
from bot.admin_func.utils import user_to_json, format_user_data
from bot.handlers.admin import ADMIN_CHAT_IDS
from models.UserCl import UserCl
import logging

router = Router()
DB_PATH = os.getenv('database_path_local')
# Начало режима обслуживания
@router.message(F.text == "Режим обслуживания")
async def start_user_service_mode(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_CHAT_IDS:
        await message.answer("У вас нет прав для использования этой команды.")
        return

    keyboard = await get_search_user_keyboard()
    await message.answer("Выберите способ поиска пользователя:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_search_method)


# Выбор метода поиска
@router.callback_query(F.data == "search_by_chat_id")
async def search_by_chat_id(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите Chat ID пользователя:")
    await state.set_state(AdminStates.waiting_for_chat_id)
    await callback.answer()


# Обработчик Chat ID
@router.message(AdminStates.waiting_for_chat_id)
async def handle_chat_id_input(message: types.Message, state: FSMContext):
    try:
        chat_id = message.text.strip()
        if not chat_id.isdigit():
            await message.answer("Chat ID должен быть числом. Попробуйте снова.")
            return

        user = await UserCl.load_user(int(chat_id))  # Загрузка пользователя
        if not user:
            await message.answer("Пользователь не найден.")
            return

        # Получение данных пользователя
        user_json = await user_to_json(user, DB_PATH)
        formatted_data = await format_user_data(user_json)
        await message.answer(f"Найден пользователь:\n{formatted_data}", parse_mode="HTML")

        # Отправка клавиатуры для действий
        keyboard = await get_user_service_keyboard()
        await message.answer("Выберите действие:", reply_markup=keyboard)

        # Сохранение данных пользователя в FSM
        await state.update_data(current_user=user)
        await state.set_state(AdminStates.waiting_for_action)

    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer("Произошла ошибка при обработке запроса.")



@router.callback_query(F.data == "cancel_service")
async def handle_cancel_service(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает отмену действия."""
    await state.clear()
    await callback.message.answer("Действие отменено.")
    await callback.answer()
