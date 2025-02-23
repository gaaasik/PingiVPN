import logging

from base_processor import BaseResultProcessor
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ResultChangeEnable(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        enable_status = task_data.get('enable')
        status_task = task_data.get('status')
        us = await UserCl.load_user(chat_id)
        if us and enable_status is not None:
            await us.active_server.enable.set_enable_admin(enable_status)
            logging.info(f"Получена и обработана задача result_change_enable. От chat_id = {chat_id}")
            await send_admin_log(bot, f"😈Пользователь {chat_id} изменил состояние на {enable_status} (в db:{us.active_server.enable.get()}), status={status_task}")

        else:
            logging.error(f"Ошибка у enable в result_change_enable. От chat_id = {chat_id}")
            await send_admin_log(bot,
                                 f"😈❌Пользователь {chat_id} НЕ изменил состояние, сейчас {us.active_server.enable.get()}, а пришло enable=NONE status={status_task}")



