import logging

from communication_with_servers.result_processor.all_processor.result_creating_user import ResultCreateUsers
from communication_with_servers.result_processor.all_processor.result_delete_user import ResultDeleteUser
from communication_with_servers.result_processor.all_processor.result_check_enable import ResultCheckEnable
from communication_with_servers.result_processor.all_processor.result_change_enable import ResultChangeEnable


class ResultTaskManager:
    def __init__(self, redis_client):
        self.task_handlers = {
            "result_delete_user": ResultDeleteUser(redis_client),
            "result_check_enable_user": ResultCheckEnable(redis_client),
            "result_change_enable_user": ResultChangeEnable(redis_client),
            "result_create_user": ResultCreateUsers(redis_client)
        }

    async def process_task(self, task_json):
        try:
            task_type = task_json.get("task_type")
            processor = self.task_handlers.get(task_type)
            if processor:
                await processor.process(task_json)
        except Exception as e:
            logging.error(f"Ошибка при определении task_type: {e}")

