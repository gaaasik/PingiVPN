from base_processor import BaseResultProcessor
from models.UserCl import UserCl


class ResultCheckEnable(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        user = await UserCl.load_user(chat_id)
        if user:
            current_status = user.active_server.enable.get()
            print(f"Статус пользователя {chat_id}: {current_status}")
