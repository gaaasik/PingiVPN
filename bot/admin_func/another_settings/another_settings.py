
import os
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from communication_with_servers.send_type_task import send_creating_user_tasks_for_servers
from models.country_server_data import get_json_country_server_data

router = Router()
PAGE_SIZE = 6  # количество серверов на страницу


# 📌 Главное меню админ-настроек
async def get_admin_settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Вывести все сервера", callback_data="view_all_servers")],
        [InlineKeyboardButton(text="♻️ Регенерация ключей", callback_data="action:regenerate")],
        [InlineKeyboardButton(text="🔄 Перезагрузка всех серверов", callback_data="action:reboot")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu_user")]
    ])


@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: CallbackQuery, state: FSMContext):
    keyboard = await get_admin_settings_keyboard()
    await callback.message.edit_text("⚙️ Административные настройки:", reply_markup=keyboard)
    await callback.answer()


# 📌 Вывести список серверов (по страницам)
@router.callback_query(F.data == "view_all_servers")
async def show_server_list(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_servers=set(), server_page=0)
    await send_server_page(callback.message, state)
    await callback.answer()


# 📌 Переключение страниц
@router.callback_query(F.data.startswith("page:"))
async def handle_page_change(callback: CallbackQuery, state: FSMContext):
    new_page = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.update_data(server_page=new_page)
    await send_server_page(callback.message, state, data.get("selected_servers", set()))
    await callback.answer()


# 📌 Тоггл выбора сервера
@router.callback_query(F.data.startswith("toggle:"))
async def toggle_server_selection(callback: CallbackQuery, state: FSMContext):
    _, ip, page = callback.data.split(":")
    data = await state.get_data()
    selected = set(data.get("selected_servers", set()))
    if ip in selected:
        selected.remove(ip)
    else:
        selected.add(ip)
    await state.update_data(selected_servers=selected, server_page=int(page))
    await send_server_page(callback.message, state, selected)
    await callback.answer()


# 📌 Действия над выбранными серверами
@router.callback_query(F.data.startswith("action:"))
async def handle_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_servers", set())
    targets = list(selected) if selected else None

    if not targets:
        await callback.answer("❗ Сначала выберите серверы", show_alert=True)
        return

    if action == "regenerate":
        print(">>> Вызван regenerate")
        await callback.message.edit_text("🛠 Регенерация ключей запущена...")
        await send_creating_user_tasks_for_servers(targets)
        await callback.message.edit_text("✅ Задачи на создание ключей отправлены.")

    elif action == "reboot":
        print(">>> Вызван reboot")
        await callback.message.edit_text(f"🔄 Перезагрузка серверов:\n{chr(10).join(targets)}")
        # Тут будет вызов перезагрузки позже

    await callback.answer()


# 📌 Отправка клавиатуры серверов
async def send_server_page(message: types.Message, state: FSMContext, selected: set = None):
    if selected is None:
        data = await state.get_data()
        selected = set(data.get("selected_servers", set()))
        page = data.get("server_page", 0)
    else:
        page = (await state.get_data()).get("server_page", 0)

    servers_data = (await get_json_country_server_data())["servers"]
    total = len(servers_data)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    current_page = servers_data[start:end]

    inline_keyboard = []

    for srv in current_page:
        ip = srv["address"]
        name = srv["name"]
        checked = "✅ " if ip in selected else ""
        button = InlineKeyboardButton(
            text=f"{checked}{name}",
            callback_data=f"toggle:{ip}:{page}"
        )
        inline_keyboard.append([button])

    pagination = []
    if page > 0:
        pagination.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page-1}"))
    if end < total:
        pagination.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page:{page+1}"))
    if pagination:
        inline_keyboard.append(pagination)

    inline_keyboard.append([
        InlineKeyboardButton(text="♻️ Регенерация", callback_data="action:regenerate"),
        InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="action:reboot")
    ])

    inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_settings")
    ])

    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await message.edit_text("🌐 Список серверов:", reply_markup=markup)
