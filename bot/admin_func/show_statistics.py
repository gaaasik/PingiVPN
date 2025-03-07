import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup  # Добавляем поддержку состояний
from datetime import datetime

from bot.admin_func.keyboards import get_statistics_keyboard
from bot.handlers.admin import ADMIN_CHAT_IDS
from models.daily_task_class.statistics_generator import generate_statistic_text

router = Router()


# Определяем класс состояний
class StatisticStates(StatesGroup):
    waiting_for_stat_date = State()


@router.callback_query(F.data == "show_statistics")
async def show_statistic_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Вывести статистику".
    """
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.message.edit_text("❌ У вас нет прав для использования этой команды.")
        await callback.answer()
        return

    try:
        stats_message = await generate_statistic_text()

        if not stats_message.strip():
            stats_message = "❌ Ошибка: статистика не получена."

    except Exception as e:
        logging.error(f"Ошибка при генерации статистики: {e}")
        stats_message = f"❌ Ошибка при генерации статистики:\n<code>{str(e)}</code>"

    keyboard = await get_statistics_keyboard()
    await callback.message.edit_text(stats_message, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()
@router.callback_query(F.data == "choose_stat_date")
async def choose_stat_date(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает у администратора дату в формате ДД.ММ.ГГГГ для получения статистики.
    """
    await callback.message.edit_text("📅 Введите дату в формате <b>ДД.ММ.ГГГГ</b> (например, <code>02.03.2025</code>):",
                                     parse_mode="HTML")

    # Устанавливаем состояние
    await state.set_state(StatisticStates.waiting_for_stat_date)

    await callback.answer()


@router.message(StatisticStates.waiting_for_stat_date)
async def process_stat_date(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод даты в формате ДД.ММ.ГГГГ и отправляет статистику за указанную дату.
    """
    try:
        selected_date = datetime.strptime(message.text.strip(), "%d.%m.%Y")  # Новый формат ДД.ММ.ГГГГ

        stats_message = await generate_statistic_text(selected_date)

        keyboard = await get_statistics_keyboard()

        # Используем edit_text, чтобы изменить старое сообщение, а не отправлять новое
        await message.answer(stats_message, reply_markup=keyboard, parse_mode="HTML")

    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате <b>ДД.ММ.ГГГГ</b>.", parse_mode="HTML")

    await state.clear()
