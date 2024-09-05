# import pytest
# from unittest.mock import AsyncMock, Mock
# from aiogram.types import Message
# from bot.handlers.admin import cmd_list_users
#
#
# @pytest.mark.asyncio
# async def test_cmd_list_users(mocker):
#     # Мокаем функцию получения всех пользователей
#     mocker.patch('bot.utils.db.get_all_users', return_value=[(1, 123456, '+123456789')])
#
#     # Создаем фейковое сообщение
#     mock_message = Mock(spec=Message)
#     mock_message.answer = AsyncMock()
#
#     # Запускаем обработчик команды
#     await cmd_list_users(mock_message)
#
#     # Проверяем, что сообщение отправлено и содержит нужный текст
#     mock_message.answer.assert_called_once()
#     assert 'список пользователей' in mock_message.answer.call_args[0][0].lower()
