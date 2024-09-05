import pytest
from unittest.mock import AsyncMock, Mock
from aiogram.types import Message
from bot.handlers.share import cmd_share


@pytest.mark.asyncio
async def test_cmd_share():
    # Создаем фейковое сообщение
    mock_message = Mock(spec=Message)
    mock_message.answer = AsyncMock()

    # Запускаем обработчик команды
    await cmd_share(mock_message)

    # Проверяем, что сообщение отправлено и содержит нужный текст
    mock_message.answer.assert_called_once()
    assert 'поделитесь этим ботом' in mock_message.answer.call_args[0][0].lower()
