import json
import asyncio
import logging

import os

import redis.asyncio as aioredis
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from bot.admin_func.history_key.moving_wg_files import generate_qr_code
from bot.handlers.admin import send_admin_log
from bot_instance import bot
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
        await send_admin_log(
            bot,
            f"⚠️ Не все сервера перезапустились за {delay_minutes} минут!\n\n"
            f"Не ответили:\n{chr(10).join(rebooted_servers_expected)}"
        )
        rebooted_servers_expected = []

    else:
        # если всё пришло до таймера, ничего не делать
        pass

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
