import logging

from .base_processor import BaseResultProcessor
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", encoding="utf-8")


class ResultCheckEnable(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        status_task = task_data.get('status')
        enable_status = task_data.get('enable')
        us = await UserCl.load_user(chat_id)
        if us:
            await us.active_server.enable.set_enable_admin(enable_status)
            current_status = await us.active_server.enable.get()
            logging.info(f"result_check_enable: Пользователь {chat_id} изменил состояние на {current_status}, status={status_task}")
            await send_admin_log(bot, f"result_check_enable: Пользователь {chat_id} изменил состояние на {current_status}, status={status_task}")
        else:
            logging.error(f"Ошибка в задаче result_check_enable. От chat_id = {chat_id}")