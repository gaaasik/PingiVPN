from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
import aiosqlite
import os

from bot_instance import bot
from bot.handlers.admin import ADMIN_CHAT_IDS, send_admin_log
from bot.states.StatesCL import FeedbackStates

router = Router()


# ========== ОБЩИЕ КНОПКИ ==========

def main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )

def skip_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="leave_feedback")]
        ]
    )


# ========== МЕНЮ ВЫБОРА ТИПА ОТЗЫВА ==========
# вооооооооот здесь
#
# тестить дальше это меню !

@router.callback_query(F.data == "leave_feedback")
async def handle_feedback(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Оценить сервис", callback_data="feedback_rating")],
            [InlineKeyboardButton(text="💡 Предложить улучшения", url="https://t.me/pingi_help")],
            [InlineKeyboardButton(text="❗ Сообщить о проблеме", url="https://t.me/pingi_help")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )
    await state.set_state(FeedbackStates.choosing_feedback_type)
    await callback.message.edit_text(
        "🙏 Нам важно ваше мнение!\nВыберите подходящий пункт ниже:",
        reply_markup=keyboard
    )


# ========== FSM: Оценка сервиса ==========

@router.callback_query(F.data == "feedback_rating")
async def start_feedback_rating(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackStates.rating_speed)
    await callback.message.edit_text(
        f"🔢 Насколько хорошо работает VPN по скорости?\n <b>Введите от 1 до 10</b>",
        reply_markup=skip_back_keyboard()
    )
    await callback.answer()

@router.message(FeedbackStates.rating_speed)
async def process_rating_speed(message: Message, state: FSMContext):
    score = message.text.strip()
    if not score.isdigit() or not (1 <= int(score) <= 10):
        await message.answer("❌ Введите число от 1 до 10",reply_markup=skip_back_keyboard(),)
        return
    await state.update_data(rating_speed=int(score))
    await state.set_state(FeedbackStates.rating_difficulty)
    await message.answer("🧩 Насколько сложно было подключиться? \n <b>Введите от 1 до 10</b>", reply_markup=skip_back_keyboard())

@router.message(FeedbackStates.rating_difficulty)
async def process_rating_difficulty(message: Message, state: FSMContext):
    score = message.text.strip()
    if not score.isdigit() or not (1 <= int(score) <= 10):
        await message.answer("❌ Введите число от 1 до 10",reply_markup=skip_back_keyboard(),)
        return
    await state.update_data(rating_difficulty=int(score))
    await state.set_state(FeedbackStates.rating_comment)
    await message.answer("🤝 Насколько вероятно, что вы порекомендуете нас другу? \n <b>Введите от 1 до 10</b>", reply_markup=skip_back_keyboard())

@router.message(FeedbackStates.rating_comment)
async def process_rating_comment(message: Message, state: FSMContext):
    recommend_score = message.text.strip()
    if not recommend_score.isdigit() or not (1 <= int(recommend_score) <= 10):
        await message.answer("❌ Введите число от 1 до 10",reply_markup=skip_back_keyboard(),)
        return

    data = await state.get_data()
    chat_id = message.chat.id
    username = message.from_user.username or "Без username"
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    rating_speed = data.get("rating_speed")
    rating_difficulty = data.get("rating_difficulty")
    recommend_score = int(recommend_score)

    # Формируем итоговое сообщение
    text = (
        f"📩 <b>Отзыв от</b> @{username} (chat_id: <code>{chat_id}</code>):\n\n"
        f"🔢 <b>Скорость:</b> {rating_speed}/10\n"
        f"🧩 <b>Сложность подключения:</b> {rating_difficulty}/10\n"
        f"🤝 <b>Порекомендовал бы другу:</b> {recommend_score}/10\n"
        f"🕒 <i>{timestamp}</i>"
    )

    await send_admin_log(bot,text)

    # Запись в базу данных
    try:
        async with aiosqlite.connect(os.getenv("database_path_local")) as db:
            await db.execute(
                """
                INSERT INTO user_questions (chat_id,user_id, question_text, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id,0, f"Оценка: {rating_speed}/10 | Сложность: {rating_difficulty}/10 | Рекомендация: {recommend_score}/10", timestamp)
            )
            await db.commit()
    except Exception as e:
        await message.answer("⚠️ Ошибка при сохранении отзыва.")
        print("DB insert error:", e)

    await message.answer("✅ Спасибо за ваш отзыв!", reply_markup=main_menu_keyboard())
    await state.clear()


# ========== Обработка кнопок предложений и жалоб ==========
#
# @router.callback_query(F.data == "feedback_suggestions")
# async def handle_suggestion(callback: CallbackQuery, state: FSMContext):
#     await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="💬 Задать вопрос", url="https://t.me/pingi_help")],
#             [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
#         ]
#     ))
#     await state.clear()
#
# @router.callback_query(F.data == "feedback_issue")
# async def handle_issue(callback: CallbackQuery, state: FSMContext):
#     await callback.answer("✉️ Сейчас откроется чат с поддержкой", show_alert=True)
#     await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/pingi_help")],
#             [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
#         ]
#     ))
#     await state.clear()
