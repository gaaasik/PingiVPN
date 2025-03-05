import os
import logging
from typing import List, Optional

import aiosqlite
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.admin_func.states import AdminStates
from bot.admin_func.searh_user.utils import user_to_json, format_user_data
from models.UserCl import UserCl
from bot.admin_func.keyboards import get_search_user_keyboard, get_user_service_keyboard  # Клавиатура для действий

router = Router()
DB_PATH = os.getenv('database_path_local')


async def get_chat_ids_by_full_name(full_name: str, db_path: str) -> List[tuple]:
    """Ищет пользователей по точному или частичному совпадению имени и фамилии."""
    try:
        async with aiosqlite.connect(db_path) as db:
            # Сначала ищем точное совпадение
            query_exact = "SELECT chat_id, user_name_full, registration_date FROM users WHERE user_name_full = ?"
            async with db.execute(query_exact, (full_name,)) as cursor:
                exact_match = await cursor.fetchone()
                if exact_match:
                    return [exact_match]  # Возвращаем точное совпадение сразу

            # Если точного совпадения нет, ищем по частичному совпадению
            query_like = "SELECT chat_id, user_name_full, registration_date FROM users WHERE user_name_full LIKE ?"
            async with db.execute(query_like, (f"%{full_name}%",)) as cursor:
                result = await cursor.fetchall()
                return result if result else []
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя по имени '{full_name}': {e}")
        return []


@router.callback_query(F.data == "search_by_full_name")
async def search_by_full_name(callback: CallbackQuery, state: FSMContext):
    """Просим пользователя ввести имя и фамилию для поиска."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
    ])

    await callback.message.edit_text("👤 Введите имя и фамилию пользователя (или часть имени):", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_full_name)
    await callback.answer()


@router.message(AdminStates.waiting_for_full_name)
async def handle_full_name_input(message: types.Message, state: FSMContext):
    """Ищет пользователя по имени и фамилии (включая частичные совпадения) и запрашивает chat_id, если найдено несколько."""
    full_name = message.text.strip()

    if not full_name:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
        ])
        await message.answer("⚠️ Имя и фамилия не могут быть пустыми. Попробуйте снова.", reply_markup=keyboard)
        return

    users = await get_chat_ids_by_full_name(full_name, DB_PATH)

    if not users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
        ])
        await message.answer("❌ Пользователь с таким именем не найден.", reply_markup=keyboard)
        return

    if len(users) == 1:
        # Если найден ровно один пользователь, загружаем его данные
        chat_id = users[0][0]
        try:
            user = await UserCl.load_user(int(chat_id))
            if not user:
                raise ValueError("Пользователь найден в БД, но данные отсутствуют.")

            await state.update_data(current_user=user)
            user_json = await user_to_json(user, DB_PATH)
            formatted_data = await format_user_data(user_json)

            keyboard = await get_user_service_keyboard()

            await message.answer(
                f"✅ Найден пользователь:\n{formatted_data}\n\nВыберите действие:",
                parse_mode="HTML",
                reply_markup=keyboard
            )

            await state.set_state(AdminStates.waiting_for_action)
        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя с Chat ID {chat_id}: {e}")
            await message.answer("❌ Произошла ошибка при загрузке данных пользователя.")
            await state.clear()
        return

    # Если найдено несколько пользователей, выводим список и просим ввести chat_id
    users_list = "🔍 <b>Найдено несколько пользователей:</b>\n\n"
    for idx, (chat_id, name, registration_date) in enumerate(users, start=1):
        users_list += f"<b>{idx}. {name}</b> | ID: <code>{chat_id}</code> | 📅: {registration_date}\n"

    users_list += "\n✏️ Введите <b>ID</b> нужного пользователя для продолжения."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_user")]
    ])
    await message.answer(users_list, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_chat_id)