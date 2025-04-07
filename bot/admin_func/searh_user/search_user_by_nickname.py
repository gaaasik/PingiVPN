import os
import logging
from typing import Optional

import aiosqlite
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.admin_func.states import AdminStates
from bot.admin_func.keyboards import get_search_user_keyboard, get_user_service_keyboard
from bot.admin_func.searh_user.utils import user_to_json, format_user_data  # Функции для получения и форматирования данных Ошибка при поиске пользователя:
from models.UserCl import UserCl  # Модель пользователя

router = Router()
DB_PATH = os.getenv('database_path_local')


async def get_chat_id_by_nickname(nickname: str, db_path: str) -> Optional[int]:
    """Ищет пользователя по user_login (никнейму) и возвращает его chat_id."""
    try:
        async with aiosqlite.connect(db_path) as db:
            query = "SELECT chat_id FROM users WHERE user_login = ?"
            async with db.execute(query, (nickname,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя по никнейму '{nickname}': {e}")
        return None


@router.callback_query(F.data == "search_by_nickname")
async def search_by_nickname(callback: CallbackQuery, state: FSMContext):
    """Просим пользователя ввести никнейм для поиска."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
    ])

    await callback.message.edit_text("🆔 Введите никнейм пользователя:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_nickname)
    await callback.answer()


@router.message(AdminStates.waiting_for_nickname)
async def handle_nickname_input(message: types.Message, state: FSMContext):
    """Ищет пользователя по никнейму и выполняет поиск по его chat_id"""
    nickname = message.text.strip()

    # Удаляем @, если он есть в начале
    if nickname.startswith("@"):
        nickname = nickname[1:]

    if not nickname:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
        ])
        await message.answer("⚠️ Никнейм не может быть пустым. Попробуйте снова.", reply_markup=keyboard)
        return

    chat_id = await get_chat_id_by_nickname(nickname, DB_PATH)

    if chat_id:
        # Если нашли Chat ID, загружаем пользователя так же, как в поиске по Chat ID
        try:
            user = await UserCl.load_user(int(chat_id))  # Загружаем пользователя
            if not user:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
                ])
                await message.answer("Пользователь найден в БД, но данные отсутствуют.", reply_markup=keyboard)
                raise ValueError("Пользователь найден в БД, но данные отсутствуют.")

            # Сохраняем найденного пользователя
            await state.update_data(current_user=user)

            # Получаем данные пользователя
            user_json = await user_to_json(user, DB_PATH)
            formatted_data = await format_user_data(user_json)

            # Кнопки действий
            keyboard = await get_user_service_keyboard()

            # Отправляем пользователю информацию
            sent_message = await message.answer(
                f"✅ Найден пользователь:\n{formatted_data}\n\nВыберите действие:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await state.update_data(last_message_id=sent_message.message_id)

            # Устанавливаем состояние
            await state.set_state(AdminStates.waiting_for_action)

        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя с Chat ID {chat_id}: {e}")
            await message.answer("❌ Произошла ошибка при загрузке данных пользователя.")
            await state.clear()

    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
        ])
        await message.answer("❌ Пользователь с таким никнеймом не найден. Попробуйте еще раз", reply_markup=keyboard)

    await state.set_state(AdminStates.waiting_for_nickname)

