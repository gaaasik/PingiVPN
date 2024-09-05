# bot/handlers/support.py
from aiogram import Router, types
from bot.utils.db import add_user_question  # Импорт функции добавления вопроса в базу данных
from aiogram import Router, types
from aiogram.filters import Command
from bot.handlers.cleanup import store_message, delete_unimportant_messages
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

# Определение состояния ожидания вопроса от пользователя
class SupportState(StatesGroup):
    waiting_for_question = State()


@router.message(Command("support"))
@router.message(lambda message: message.text == "Задать вопрос 🙋‍♂️")
async def cmd_support(message: types.Message, state: FSMContext):
    await store_message(message.chat.id, message.message_id, message.text, 'user')
    await state.set_state(SupportState.waiting_for_question)
    response = await message.answer(
        "Если у вас возникли вопросы или проблемы, пожалуйста напишите вашу проблему и мы с вами свяжемся : ")
    # Сохраняем сообщение в базе данных
    await store_message(response.chat.id, response.message_id, response.text, 'bot')

    current_state = await state.get_state()
    print(f"Current state: {current_state}")  # Добавьте вывод текущего состояния для проверки

    await delete_unimportant_messages(message.chat.id, message.bot)

# Обработчик для получения вопроса от пользователя
@router.message(SupportState.waiting_for_question)
async def process_user_question(message: types.Message, state: FSMContext):
    # Сохраняем вопрос пользователя в базу данных
    await add_user_question(message.chat.id, message.from_user.id, message.text)

    # Сохраняем ID сообщения пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Отправляем пользователю подтверждение
    confirmation_message = await message.answer("Ваш вопрос записан, ожидайте ответа!")
    await store_message(confirmation_message.chat.id, confirmation_message.message_id, confirmation_message.text, 'bot')

    # Завершаем состояние ожидания вопроса
    await state.clear()

    # Удаляем неважные сообщения
    await delete_unimportant_messages(message.chat.id, message.bot)
