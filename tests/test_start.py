# test/test_start.py
import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from bot.handlers.start import cmd_start
from bot.utils.db import add_user, get_user_by_telegram_id


@pytest.mark.asyncio
async def test_start_command():
    # Мок объекты
    bot = Bot(token='7036736465:AAEOlcvkYEp3MrEaS1Md0iR8Xilgti6cFuU')
    dp = Dispatcher()
    message = Message(chat={"id": 123456}, from_user={"id": 123456, "username": "test_user"})

    # Вызываем команду
    await cmd_start(message=message, state=None)

    # Проверяем, что пользователь добавлен
    user = await get_user_by_telegram_id(message.from_user.id)
    assert user is not None
    print(f"Команда /start успешно выполнилась для пользователя {message.from_user.username}.")
