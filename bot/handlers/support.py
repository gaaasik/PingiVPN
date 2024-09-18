# bot/handlers/support.py
from aiogram import Router, types
from bot.utils.db import add_user_question  # Импорт функции добавления вопроса в базу данных
from aiogram import Router, types
from aiogram.filters import Command
from bot.handlers.cleanup import store_message, delete_unimportant_messages, register_message_type
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()
support_message = "Если у вас возникли вопросы или проблемы, пожалуйста напишите вашу проблему и мы с вами свяжемся : "
# Определение состояния ожидания вопроса от пользователя
class SupportState(StatesGroup):
    waiting_for_question = State()


@router.message(Command("support"))
@router.message(lambda message: message.text == "Задать вопрос 🙋‍♂️")
async def cmd_support(message: types.Message, state: FSMContext):
    await store_message(message.chat.id, message.message_id, message.text, 'user')
    chat_id = message.chat.id
    user_id = message.from_user.id
    bot = message.bot
    await state.set_state(SupportState.waiting_for_question)

    response = await message.answer(text=support_message
                                    )
    # Сохраняем сообщение в базе данных
    await store_message(response.chat.id, response.message_id, response.text, 'bot')
    await register_message_type(chat_id, response.message_id, 'support_message', 'bot')
    current_state = await state.get_state()
    print(f"Current state: {current_state}")  # Добавьте вывод текущего состояния для проверки
    # Регистрируем тип сообщения для маппинга, чтобы можно было его удалять
    if response:
        await store_message(chat_id, response.message_id, support_message, 'bot')
        await register_message_type(chat_id, response.message_id, 'share_friends',
                                    'bot')  # Оставляем await, т.к. функция асинхронная
    else:
        print("Ошибка отправки сообщения: message.answer вернул None")

    # Удаляем неважные сообщения
    await delete_unimportant_messages(chat_id, bot)


# Обработчик для получения вопроса от пользователя
@router.message(SupportState.waiting_for_question)
async def process_user_question(message: types.Message, state: FSMContext):
    # Сохраняем вопрос пользователя в базу данных
    await add_user_question(message.chat.id, message.from_user.id, message.text)
    username = message.from_user.username or str(message.from_user.id)
    # Сохраняем ID сообщения пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Отправляем пользователю подтверждение
    confirmation_message = await message.answer(f"Ваш вопрос записан \n\n {message.text} \n\n Ожидайте ответа!")
    await register_message_type(confirmation_message.chat.id, confirmation_message.message_id, 'question_from_user', 'bot')
    await store_message(confirmation_message.chat.id, confirmation_message.message_id, confirmation_message.text, 'bot')
    await message.bot.send_message(
        chat_id=456717505,  # ID админа для уведомления
        text=f"Пользователь задал вопрос: @{username} (ID чата: {message.chat.id}) \n Задал вопрос: {message.text}"
    )
    # Завершаем состояние ожидания вопроса
    await state.clear()

    # Удаляем неважные сообщения
    await delete_unimportant_messages(message.chat.id, message.bot)
