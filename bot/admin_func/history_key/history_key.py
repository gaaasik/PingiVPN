import logging
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Chat, User, Message

from bot.admin_func.searh_user.search_user_handlers import handle_main_menu_user
from bot.admin_func.searh_user.utils import format_history_key
from bot.admin_func.states import AdminStates
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl
from dotenv import load_dotenv

router = Router()
load_dotenv()

############Толян начал ебашить кнопки     Запустилась функция _______move_in_history_files_wg

def button_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu_user")]
        ]
    )
def button_search_by_chat_id_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="search_by_chat_id")]
        ]
    )


@router.callback_query(lambda c: c.data.startswith("history_key_show_"))
async def handle_history_key_show(callback: CallbackQuery, state: FSMContext):
    """Выводит информацию о выбранном ключе из history_key_list."""
    logging.info("Зашли в history_key_show_")

    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        logging.error("Ошибка: current_user отсутствует в state.")
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.", reply_markup=button_search_by_chat_id_keyboard())
        return

    if not user.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.",  reply_markup=button_back_keyboard())
        return

    chat_id = user.chat_id
    us = await UserCl.load_user(chat_id)
    if not us or not us.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.",  reply_markup=button_back_keyboard())
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
    await state.update_data(last_message_id=key_info.message_id)
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
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu_user")]) #search_by_chat_id
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# @router.callback_query(F.data == "my_back_menu")
# async def handler_my_back_menu(callback: CallbackQuery, state: FSMContext):
#     """Возвращает в состояние ожидания ввода Chat ID."""
#     logging.info("Зашли в my_back_menu")
#
#     data = await state.get_data()
#     user = data.get("current_user")
#
#     await state.update_data(current_user=user)
#     # Меняем пользователя
#     await state.set_state(AdminStates.main_menu_user)
#     await handle_main_menu_user(callback.message, state)
#     await callback.answer()

@router.callback_query(lambda c: c.data.startswith("change_active_server_"))
async def handler_change_active_server(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    last_message_id = data.get("last_message_id")
    if last_message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=last_message_id)
        except Exception:
            pass  # Игнорируем ошибки удаления
    from bot.admin_func.history_key.moving_wg_files import move_in_history_files_wg, move_in_user_files_wg
    """Возвращает в состояние ожидания ввода Chat ID."""
    logging.info("Запуск change_active_server_")
    data = await state.get_data()
    user = data.get("current_user")
    us = await UserCl.load_user(user.chat_id)
    index = int(callback.data.split("_")[-1])
    if us.active_server:
        old_key = us.active_server
        logging.error(f"у пользователя {us.chat_id} нету active_server")
    new_key = us.history_key_list[index]
    del us.history_key_list[index]
    await new_key.date_key_off.set(await old_key.date_key_off.get())
    us.history_key_list.append(old_key)
    us.servers.remove(old_key)
    us.servers.append(new_key)
    await us.choosing_working_server()
    logging.info("Из history_key_list удален выбранный ключ и добавлен старый ключ")
    await us.push_field_json_in_db("history_key_list")
    await us.push_field_json_in_db("servers")
    logging.info("Обновил базу данных ")
    
    await new_key.enable.set(True)
    await old_key.enable.set(False)
    logging.info("Отключил old_key, включил new_key")

    # Если старый ключ wireguard, значит нужно его переместить в history_key
    if await old_key.name_protocol.get() == "wireguard":
        await move_in_history_files_wg(old_key)
    # Если новый ключ wireguard, значит нужно его вытащить из history_key
    if await new_key.name_protocol.get() == "wireguard":
        await move_in_user_files_wg(new_key)

    await send_admin_log(bot,f"🆕 Администратор {callback.message.chat.id} изменил основной ключ у {us.chat_id} c {await old_key.name_protocol.get() if old_key else '$ключа не было$'} на {await new_key.name_protocol.get()}")
    await callback.message.answer(f"Изменил основной ключ у пользователя с chat_id {user.chat_id}.")
    await state.set_state(AdminStates.main_menu_user)
    await state.update_data(current_user=user)
    # Меняем пользователя
    await state.set_state(AdminStates.main_menu_user)
    await handle_main_menu_user(callback, state)
    await callback.answer()





