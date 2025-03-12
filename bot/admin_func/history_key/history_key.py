import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.admin_func.searh_user.utils import format_history_key
from bot.admin_func.states import AdminStates
from models.UserCl import UserCl

router = Router()


############Толян начал ебашить кнопки


@router.callback_query(lambda c: c.data.startswith("history_key_show_"))
async def handle_history_key_show(callback: CallbackQuery, state: FSMContext):
    """Выводит информацию о выбранном ключе из history_key_list."""
    logging.info("Зашли в history_key_show_")

    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        logging.error("Ошибка: current_user отсутствует в state.")
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    if not user.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.")
        return

    chat_id = user.chat_id
    us = await UserCl.load_user(chat_id)
    if not us or not us.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.")
        return

    # Получаем индекс выбранного ключа
    index = int(callback.data.split("_")[-1])
    selected_key = us.history_key_list[index]

    # Сохраняем индекс выбранного ключа в state
    await state.update_data(selected_history_index=index)

    # Формируем сообщение с помощью format_history_key
    key_info = await format_history_key(selected_key, index)
    keyboard = await generate_history_keyboard(us.history_key_list, index)

    await callback.message.edit_text(key_info, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def generate_history_keyboard(history_key_list, selected_index):
    """Создает клавиатуру с историей ключей."""
    buttons = []
    index = 0
    for i, key in enumerate(history_key_list):
        name = await key.name_server.get()
        if i == selected_index:
            index = i
            prefix = "📍 "
        else:
            prefix = ""

        buttons.append([InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"history_key_show_{i}")])
    buttons.append([InlineKeyboardButton(text="✅ Сделать сервер основным", callback_data=f"change_active_server_{index}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_chat_id")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "back_to_chat_id")
async def back_to_chat_id(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    await callback.message.edit_text("🔢 Введите Chat ID пользователя:")
    await state.set_state(AdminStates.waiting_for_chat_id)  # Устанавливаем состояние
    await callback.answer()


@router.callback_query(F.data == "change_active_server_")
async def back_to_chat_id(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    data = await state.get_data()
    user = data.get("current_user")
    us = await UserCl.load_user(user.chat_id)
    index = int(callback.data.split("_")[-1])
    back_old_active_server = us.active_server
    back_new_server = us.history_key_list[index]

    us.active_server.status_key.set(back_new_server.server_ip)


    await callback.answer()
