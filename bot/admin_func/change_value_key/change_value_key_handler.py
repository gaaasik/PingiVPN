from aiogram import Router, types, F
from aiogram.types import CallbackQuery, Message, Document
from aiogram.fsm.context import FSMContext
from bot.admin_func.keyboards import get_key_change_keyboard
from bot.admin_func.states import AdminStates
import re

router = Router()

# Регулярное выражение для проверки VLESS ключа
VLESS_PATTERN = re.compile(r'vless://[a-f0-9\-]+@[0-9\.]+:\d+\?.*')


@router.callback_query(F.data == "change_to_vless")
async def change_to_vless(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на VLESS'. Запрашивает новый ключ."""
    await callback.message.edit_text("✏️ Введите новый VLESS ключ:")
    await state.set_state(AdminStates.waiting_for_vless_key)
    await callback.answer()


@router.callback_query(F.data == "change_to_wireguard")
async def change_to_wireguard(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на WireGuard'. Запрашивает файл конфигурации."""
    await callback.message.edit_text("📁 Отправьте новый файл WireGuard:")
    await state.set_state(AdminStates.waiting_for_wireguard_file)
    await callback.answer()


@router.message(AdminStates.waiting_for_vless_key)
async def process_vless_key(message: Message, state: FSMContext):
    """Обработчик ввода нового VLESS ключа."""
    chat_id = message.chat.id  # Получаем chat_id пользователя
    key = message.text.strip()

    if not VLESS_PATTERN.match(key):
        await message.answer("❌ Неверный формат VLESS ключа. Пожалуйста, введите корректный ключ.")
        return




    # Вызов функции обновления ключа





    await message.answer("✅ Новый VLESS ключ сохранен.")
    await state.clear()


@router.message(AdminStates.waiting_for_wireguard_file, F.document)
async def process_wireguard_file(message: Message, state: FSMContext):
    """Обработчик загрузки нового конфигурационного файла WireGuard."""
    chat_id = message.chat.id
    document: Document = message.document

    if not document.file_name.endswith(".conf"):
        await message.answer("❌ Ошибка: загруженный файл должен быть в формате .conf")
        return




    # Вызов функции обновления ключа




    await message.answer("✅ Файл конфигурации WireGuard получен.")
    # Здесь можно добавить код для скачивания файла и проверки его содержимого

    await state.clear()
