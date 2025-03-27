from aiogram import Router, types, F
from aiogram.types import CallbackQuery, Message, Document, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.admin_func.states import AdminStates
import re

from models.UserCl import UserCl

router = Router()

# Регулярное выражение для проверки VLESS ключа
VLESS_PATTERN = re.compile(r'vless://[a-f0-9\-]+@[0-9\.]+:\d+\?.*')

# --- Клавиатуры ---

def vless_key_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Вставить из буфера", callback_data="paste_vless_key")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )

def wireguard_key_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Загрузить из буфера", callback_data="paste_wireguard_file")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )

# --- Обработчики ---

@router.callback_query(F.data == "change_to_vless")
async def change_to_vless(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на VLESS'. Запрашивает новый ключ."""
    await callback.message.edit_text(
        "✏️ Введите новый VLESS ключ или вставьте его из буфера:",
        reply_markup=vless_key_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_vless_key)
    await callback.answer()


@router.callback_query(F.data == "change_to_wireguard")
async def change_to_wireguard(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на WireGuard'. Запрашивает файл конфигурации."""
    await callback.message.edit_text(
        "📁 Загрузите новый конфигурационный файл WireGuard или воспользуйтесь буфером:",
        reply_markup=wireguard_key_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_wireguard_file)
    await callback.answer()

# --- Заглушки на кнопки из буфера ---
@router.callback_query(F.data == "paste_vless_key")
async def handle_paste_vless(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "📋 Функция вставки из буфера скоро будет доступна. Вставьте ключ вручную.",
        show_alert=True
    )
    await state.clear()


@router.callback_query(F.data == "paste_wireguard_file")
async def handle_paste_wireguard(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "📁 Загрузка из буфера пока не реализована. Пожалуйста, отправьте `.conf` файл вручную.",
        show_alert=True
    )
    await state.clear()

# --- Приём текста VLESS ключа ---

@router.message(AdminStates.waiting_for_vless_key)
async def process_vless_key(message: Message, state: FSMContext):
    """Обработчик ввода нового VLESS ключа."""
    data = await state.get_data()
    us = data.get("current_user")
    key = message.text.strip()

    if not VLESS_PATTERN.match(key):
        await message.answer("❌ Неверный формат VLESS ключа. Пожалуйста, введите корректный ключ.")
        return

    await us.update_key_to_vless(key)
    await message.answer("✅ Новый VLESS ключ сохранён.")
    await state.clear()

# --- Приём файла WireGuard ---

@router.message(AdminStates.waiting_for_wireguard_file, F.document)
async def process_wireguard_file(message: Message, state: FSMContext):
    """Обработчик загрузки нового конфигурационного файла WireGuard."""
    data = await state.get_data()
    us = data.get("current_user")
    document: Document = message.document

    if not document.file_name.endswith(".conf"):
        await message.answer("❌ Ошибка: загруженный файл должен быть в формате .conf")
        return

    # Здесь должен быть парсинг/обработка содержимого файла
    await us.update_key_to_wireguard()

    await message.answer("✅ Файл конфигурации WireGuard получен и сохранён.")
    await state.clear()
