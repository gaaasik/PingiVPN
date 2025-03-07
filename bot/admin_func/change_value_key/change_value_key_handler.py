from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.admin_func.keyboards import get_key_change_keyboard
from bot.admin_func.states import AdminStates
import re
from aiogram.types import Message
from aiogram.types import Document

router = Router()


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


