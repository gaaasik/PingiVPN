from base_processor import BaseResultProcessor
from models.UserCl import UserCl


class ResultDeleteUser(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        user = await UserCl.load_user(chat_id)
        if user and user.active_server:
            await user.active_server.delete()
            print(f"Ключи пользователя {chat_id} удалены.")
