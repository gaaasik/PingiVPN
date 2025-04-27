
from typing import Dict
from logging_config.my_logging import my_logging
from task_processor.protocols.wireguard import WireGuardProcessor
from task_processor.protocols.vless import VlessProcessor

class TaskManager:
    """Обработчик задач из Redis."""

    def __init__(self):
        self.processors = {
            "wireguard": WireGuardProcessor(),
            "vless": VlessProcessor(),
        }

    async def process_task(self, task_data: Dict):
        my_logging.info(f"Получена задача: {task_data}")
        task_type = task_data.get("task_type")
        protocol = task_data.get("name_protocol").lower()
        processor = self.processors.get(protocol)

        if not processor:
            my_logging.error(f"Неизвестный протокол: {protocol}")
            return
        if task_type == "change_enable_user":
            await processor.process_change_enable_user(task_data)
        elif task_type == "check_enable_user":
            await processor.process_check_enable_user(task_data)
        elif task_type == "delete_user":
            await processor.process_delete_user(task_data)
        elif task_type == "creating_user":
            await processor.process_creating_user(task_data)
        elif task_type == "update_and_reboot_server":
            await processor.process_update_and_reboot_server(task_data)
        elif task_type == "create_xui_inbound":
            await VlessProcessor.create_xui_inbound_from_task()
        else:
            await processor.process_change_enable_user(task_data)
            my_logging.error(f"Неизвестный тип задачи: {task_type}")