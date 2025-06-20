
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import asyncio

from bot.admin_func.states import AdminStates

router = Router()

# ---------- Старт добавления нового сервера ----------
@router.callback_query(F.data == "add_new_server")
async def start_add_server(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Сначала выберите тип сервера:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="VLESS", callback_data="server_type_vless")],
            [InlineKeyboardButton(text="WireGuard", callback_data="server_type_wireguard")]
        ])
    )
    await state.set_state(AdminStates.choosing_server_type)
    await callback.answer()

# ---------- Выбор типа сервера ----------
@router.callback_query(F.data.in_(["server_type_vless", "server_type_wireguard"]))
async def choose_server_type(callback: CallbackQuery, state: FSMContext):
    server_type = callback.data.replace("server_type_", "")
    await state.update_data(server_type=server_type)

    await callback.message.answer("Введите IP-адрес нового сервера:")
    await state.set_state(AdminStates.waiting_ip)
    await callback.answer()

# ---------- Ввод IP адреса ----------
@router.message(AdminStates.waiting_ip)
async def input_server_ip(message: Message, state: FSMContext):
    ip_address = message.text.strip()

    if len(ip_address.split(".")) != 4:
        await message.answer("❌ Неверный IP-адрес. Попробуйте ещё.")

        return

    await state.update_data(ip_address=ip_address)
    await message.answer("Введите пароль root для сервера:")
    await state.set_state(AdminStates.waiting_password)


# ---------- Ввод пароля ----------
@router.message(AdminStates.waiting_password)
async def input_server_password(message: Message, state: FSMContext):
    password = message.text.strip()
    await state.update_data(password=password)

    await message.answer(
        "💡 Вы уверены, что хотите добавить этот сервер?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_add_server")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="cancel_add_server")]
        ])
    )




# ---------- Подтверждение или отмена ----------
@router.callback_query(F.data == "confirm_add_server")
async def confirm_add_server(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ip_address = data.get("ip_address")
    password = data.get("password")
    server_type = data.get("server_type")

    await callback.message.answer(f"🔄 Подключаемся к {ip_address}...")

    await state.set_state(AdminStates.processing)

    try:
        pass
        #await process_server_setup(ip_address, password, server_type, callback.message)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка добавления: {e}")
    finally:
        await state.clear()


@router.callback_query(F.data == "cancel_add_server")
async def cancel_add_server(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Добавление сервера отменено.")
    await state.clear()

