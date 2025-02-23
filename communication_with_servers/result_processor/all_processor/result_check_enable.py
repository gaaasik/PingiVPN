import logging

from base_processor import BaseResultProcessor
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ResultCheckEnable(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        status_task = task_data.get('status')
        us = await UserCl.load_user(chat_id)
        if us:
            logging.info(f"Получена и обработана задача result_check_enable. От chat_id = {chat_id}")
            current_status = us.active_server.enable.get()
            print(f"Статус пользователя {chat_id}: {current_status}")
            await send_admin_log(bot,
                                 f"result_check_enable: Пользователь {chat_id} изменил состояние на {current_status}, status={status_task}")
        else:
            logging.error(f"Ошибка в задаче result_check_enable. От chat_id = {chat_id}")