# bot/handlers/support.py
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.db import add_user_question  # Импорт функции добавления вопроса в базу данных
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from bot.handlers.all_menu.main_menu import show_main_menu
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()
support_message = "Если у вас возникли вопросы или проблемы, пожалуйста напишите вашу проблему и мы с вами свяжемся : "


# Определение состояния ожидания вопроса от пользователя
class SupportState(StatesGroup):
    waiting_for_question = State()


# Кнопка отмены вопроса
cancel_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_question")]
    ]
)



@router.callback_query(lambda c: c.data == "help_ask_question")
async def handle_ask_question(callback_query: CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    bot = callback_query.bot

    # Устанавливаем состояние для ожидания вопроса от пользователя
    await state.set_state(SupportState.waiting_for_question)

    # Отправляем сообщение с запросом вопроса и инлайн-кнопкой "Отменить"
    sent_message = await bot.send_message(chat_id, text=support_message, reply_markup=cancel_keyboard)

    # Выводим текущее состояние для отладки
    current_state = await state.get_state()
    print(f"Текущее состояние: {current_state}")

    # Подтверждаем callback_query
    await callback_query.answer()


# Обработчик для получения вопроса от пользователя
@router.message(SupportState.waiting_for_question)
async def process_user_question(message: types.Message, state: FSMContext):
    # Сохраняем вопрос пользователя в базу данных
    await add_user_question(message.chat.id, message.from_user.id, message.text)
    username = message.from_user.username or str(message.from_user.id)
    # Сохраняем ID сообщения пользователя

    # Отправляем пользователю подтверждение
    confirmation_message = await message.answer(f"Ваш вопрос записан \n\n {message.text} \n\n Ожидайте ответа!")

    await message.bot.send_message(
        chat_id=456717505,  # ID админа для уведомления
        text=f"Пользователь задал вопрос: @{username} (ID чата: {message.chat.id}) \n Задал вопрос: {message.text}"
    )
    # Завершаем состояние ожидания вопроса
    await state.clear()
    await show_main_menu(message.chat.id, message.bot)


@router.callback_query(lambda c: c.data == "cancel_question")
async def handle_cancel_question(callback_query: CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot

    # Очищаем состояние FSM
    await state.clear()

    # Уведомляем пользователя об отмене и отправляем главное меню
    await bot.send_message(chat_id, "❌ Ваш запрос на помощь отменён.")
    await show_main_menu(chat_id, bot)

    # Подтверждаем callback_query
    await callback_query.answer()
