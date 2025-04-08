import logging
from .base_processor import BaseResultProcessor
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", encoding="utf-8")


class ResultDeleteUser(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        us = await UserCl.load_user(chat_id)
        if us and us.active_server:
            #await us.active_server.delete()
            logging.info(f"Получена и обработана задача result_delete_enable. От chat_id = {chat_id}")
        else:
            logging.error(f"Ошибка задачи result_delete_enable. От chat_id = {chat_id}")

