import json
import asyncio
import logging

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from communication_with_servers.error_handler_queue import QueueErrorHandler
from communication_with_servers.result_processor.all_processor.base_processor import BaseResultProcessor

# Глобальный счётчик и список серверов для отслеживания перезапуска

rebooted_servers_expected = []



async def monitor_reboot_timeout(delay_minutes=5):
    """
    Ожидает заданное время и проверяет, остались ли неотвеченные сервера.
    """
    await asyncio.sleep(delay_minutes * 60)
    global rebooted_servers_expected
    if rebooted_servers_expected:  # если список не пуст — значит кто-то не ответил
        from models.country_server_data import get_name_server_by_ip  # если ещё не импортировано

        lines = []
        for ip in rebooted_servers_expected:
            server_name = await get_name_server_by_ip(ip)
            if server_name:
                lines.append(f"{server_name} – {ip}")
            else:
                lines.append(f"Неизвестный сервер – {ip}")

        message_text = (
            f"⚠️⚠️ Не все сервера перезапустились за {delay_minutes} минут!\n\n"
            f"Не ответили:\n{chr(10).join(lines)}"
        )

        await send_admin_log(bot, message_text)

        # Очистка задач из очередей
        cleaner = QueueErrorHandler()
        for ip in rebooted_servers_expected:
            await cleaner.remove_tasks_from_queue(server_ip=ip, task_type="update_and_reboot_server")
        rebooted_servers_expected = []



class UpdateAndRebootServer(BaseResultProcessor):
    """Обработчик результата перезагрузки и обновления конфигурации серверов."""
    async def process(self, task_data: dict):
        global rebooted_servers_expected

        try:
            server_ip = task_data.get("server_ip")
            if server_ip in rebooted_servers_expected:
                rebooted_servers_expected.remove(server_ip)
                if not rebooted_servers_expected:
                    await send_admin_log(bot, f"✅ Все сервера перезагрузились успешно.")

            logging.info(f"✅ Сервер {server_ip} успешно перезагрузился. Осталось: {len(rebooted_servers_expected)}")
        except Exception as e:
            logging.error(f"Ошибка в обработчике UpdateAndRebootServer: {e}")
