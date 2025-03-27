from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states.StatesCL import FeedbackStates

router = Router()

@router.callback_query(F.data == "leave_feedback")
async def handle_feedback(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Оценить сервис", callback_data="feedback_rating")],
            [InlineKeyboardButton(text="💡 Предложить улучшения", callback_data="feedback_suggestions")],
            [InlineKeyboardButton(text="❗ Сообщить о проблеме", callback_data="feedback_issue")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )

    await state.set_state(FeedbackStates.choosing_feedback_type)
    await callback.message.edit_text(
        "🙏 Нам важно ваше мнение!\nВыберите подходящий пункт ниже:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.in_(["feedback_rating", "feedback_suggestions", "feedback_issue"]))
async def feedback_placeholder(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="leave_feedback")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )

    await callback.message.edit_text(
        "⚙️ Этот функционал скоро будет доступен. Мы работаем над расширением возможностей! 💡",
        reply_markup=keyboard
    )
