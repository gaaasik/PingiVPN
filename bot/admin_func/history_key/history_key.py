import logging
from datetime import datetime

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Chat, User, Message

from bot.admin_func.searh_user.search_user_handlers import handle_chat_id_input
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
    buttons.append([InlineKeyboardButton(text="✅ Сделать ключ основным", callback_data=f"change_active_server_{index}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_back_menu")]) #search_by_chat_id
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "my_back_menu")
async def my_back_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    logging.info("Зашли в my_back_menu")

    data = await state.get_data()
    user = data.get("current_user")
    if not user:
        logging.error("Ошибка: current_user отсутствует в state.")
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    print("user.chat_id = ", user.chat_id)

    # Создаем фейковое сообщение
    fake_message = Message(
        message_id=callback.message.message_id,  # Берем ID текущего сообщения
        from_user=User(id=1388513042, is_bot=False, first_name="Admin"),  # Фейковый отправитель
        chat=Chat(id=callback.message.chat.id, type="private"),  # Используем ID текущего чата
        text=str(user.chat_id),  # Передаем chat_id как текст
        date=datetime.utcnow()  # Обязательное поле date
    )

    # Передаем fake_message вместо chat_id
    await handle_chat_id_input(fake_message, state)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("change_active_server_"))
async def handler_change_active_server(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    logging.info("Запуск change_active_server_")
    data = await state.get_data()
    user = data.get("current_user")
    us = await UserCl.load_user(user.chat_id)
    index = int(callback.data.split("_")[-1])
    back_old_active_server = us.active_server
    back_new_server = us.history_key_list[index]
    await us.history_key_list[index].delete()

    if await back_new_server.name_protocol.get() == "wireguard":
        json_dire = {
            "server_ip": await back_new_server.server_ip.get(),
            "user_ip": await back_new_server.user_ip.get()
        }
        await us.update_key_to_wireguard(json_dire)
    elif await back_new_server.name_protocol.get() == "vless":
        await us.update_key_to_vless(await back_new_server.url_vless.get())

    print(f"date_key_off у нового ключа = {await us.active_server.date_key_off.get()}")
    await callback.message.answer(f"Изменил основной ключ у пользователя с chat_id {user.chat_id}.")
    await state.set_state(AdminStates.waiting_for_bonus_days)
    await my_back_menu()

    await callback.answer()
