# test/test_file_manager.py
import os
import pytest
from bot.utils.file_manager import process_user_files

@pytest.mark.asyncio
async def test_process_user_files():
    chat_id = 123456
    folder_name = f"{chat_id}_test_user"

    # Вызываем функцию для генерации файлов
    config_file, qr_code_file = await process_user_files(folder_name)

    # Проверяем, что файлы созданы
    assert os.path.exists(config_file.path)
    assert os.path.exists(qr_code_file.path)
    print(f"Файлы конфигурации успешно созданы для пользователя с chat_id {chat_id}.")
