import pytest
from unittest.mock import AsyncMock, Mock
from aiogram.types import Message
from bot.handlers.status import cmd_status


@pytest.mark.asyncio
async def test_cmd_status(mocker):
    # Мокаем функцию получения статуса пользователя
    mocker.patch('bot.utils.db.get_user_status', return_value=('2023-08-30 12:00:00.000', 'testuser'))

    # Создаем фейковое сообщение
    mock_message = Mock(spec=Message)
    mock_message.from_user.id = 123456
    mock_message.answer = AsyncMock()

    # Запускаем обработчик команды
    await cmd_status(mock_message)

    # Проверяем, что сообщение отправлено и содержит нужный текст
    mock_message.answer.assert_called_once()
    assert 'вы с нами уже' in mock_message.answer.call_args[0][0].lower()
