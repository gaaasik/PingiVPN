import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.handlers.admin import ADMIN_CHAT_IDS
from models.daily_task_class.DailyTaskManager import DailyTaskManager

router = Router()


@router.callback_query(F.data == "show_statistics")
async def show_statistic_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Вывести статистику".
    """
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.message.answer("У вас нет прав для использования этой команды.")
        await callback.answer()
        return

    try:
        # Создаем экземпляр DailyTaskManager и вызываем метод генерации статистики
        task_manager = DailyTaskManager(callback.bot)
        await task_manager.generate_statistics()
    except Exception as e:
        logging.error(f"Ошибка при генерации статистики: {e}")
        await callback.message.answer("❌ Произошла ошибка при генерации статистики.")

    await callback.answer()
