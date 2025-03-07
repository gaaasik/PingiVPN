from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

# 📌 Заглушка для кнопки "⚙️ Админ-настройки"
@router.callback_query(F.data == "admin_settings")
async def admin_settings_placeholder(callback: CallbackQuery):
    """Выводит сообщение-заглушку для будущих админ-настроек."""
    await callback.answer("⚙️ Здесь появятся административные настройки в будущем!", show_alert=True)
