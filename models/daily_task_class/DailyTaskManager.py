import os
import logging
from datetime import datetime, timedelta
from models.daily_task_class.statistics_generator import generate_statistic_text  # Импорт новой функции

from pathlib import Path

import aiofiles

from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
from redis_configs.redis_settings import redis_client_main
from models.UserCl import UserCl
from models.referral_class.ReferralCL import ReferralCl
#Надо проработать!!!!!!!!!!!



class DailyTaskManager:
    def __init__(self, bot):
        self.bot = bot

    async def generate_statistics(self):
        """
        Генерация ежедневной статистики и отправка в чат администратора. Добавлен пользователь queue_results_task
    # async def count_remaining_vless_links(self) -> int:
    #     """
    #     Подсчитывает количество оставшихся VLESS ссылок в файле.
    #     """
    #     global url_vless_new_path
    #     try:
    #         # Получаем путь к директории из переменной окружения
    #         config_dir = os.getenv("CONFIGS_DIR")
    #         if not config_dir:
    #             logging.error("Переменная окружения CONFIGS_DIR не установлена!")
    #             return 0
    #
    #         # Полный путь к файлу
    #         url_vless_new_path = os.path.join(config_dir, "url_vless_new")
    #
    #         logging.info(f"Открываем файл: {url_vless_new_path}")
    #
    #         async with aiofiles.open(url_vless_new_path, "r") as file:
    #             urls = await file.readlines()
    #
    #         # Фильтруем только строки, содержащие ссылки vless://
    #         remaining_urls = [url.strip() for url in urls if url.strip().startswith("vless://")]
    #         count_remaining = len(remaining_urls)
    #
    #         logging.info(f"Количество оставшихся ссылок: {count_remaining}")
    #
    #         return count_remaining
    #
    #     except FileNotFoundError:
    #         logging.error(f"Файл {url_vless_new_path} не найден!")
    #         return 0
    #     except Exception as e:
    #         logging.error(f"Ошибка при чтении файла VLESS: {e}")
    #         return 0
    #
    # async def generate_statistics(self):
    #     """
    #     Генерация ежедневной статистики и отправка в чат администратора. Добавлен пользователь
    #     """
    #
    #
    #     # project_root = Path(__file__).resolve().parent.parent
    #     # url_vless_new_path = project_root / "configs" / "url_vless_new"
    #     # async with aiofiles.open(url_vless_new_path, "r") as file:
    #     #     urls = await file.readlines()
    #     remaining_urls = await self.count_remaining_vless_links()
    #
    #     yesterday = datetime.now() - timedelta(days=1)
    #     new_users = await UserCl.count_users_by_date(yesterday)
    #     total_users = len(await UserCl.get_all_users())
    #     paid_users = await UserCl.count_paid_users_by_date(yesterday)
    #     total_paid_users = await UserCl.count_total_paid_users(datetime(2024, 11, 24))
    #
    #     remaining_configs = await self.get_remaining_configs()
    #     count_regeneration_user = await redis_client.get("new_vless_users_today")
    #
    #     stats_message = (
    #         f"📊 <b>Ежедневная статистика</b> 📊\n\n"
    #         f"🗓 <b>Дата статистики за :</b> {yesterday.strftime('%Y-%m-%d')}\n"
    #         f"👥 <b>Новых пользователей:</b> {new_users}\n"
    #         f"🔑 <b>Осталось конфигурационных файлов WG:</b> {remaining_configs}\n"
    #         f"🔑 <b>Осталось ссылок url vless:</b> {remaining_urls}\n"
    #         f"🔑 <b>Сгенерировано новых ссылок url vless:</b> {count_regeneration_user}\n"
    #         f"🌍 <b>Всего пользователей:</b> {total_users}\n"
    #         f"💳 <b>Оплатили вчера:</b> {paid_users}\n"
    #         f"💳 <b>Всего оплат с 24.11.2024:</b> {total_paid_users}"
    #     )
    #
    #     await send_admin_log(self.bot, stats_message
    #
    async def show_statistic(self, date: datetime = None):
        """
        Получает текст статистики за указанную дату и отправляет администратору.
        По умолчанию — за вчера.
        """
        try:
            stats_message = await generate_statistic_text(date)
            await send_admin_log(self.bot, stats_message)
            return stats_message

        except Exception as e:
            logging.error(f"Ошибка при отправке статистики: {e}")
            return f"❌ Ошибка при отправке статистики:\n<code>{str(e)}</code>"

    async def update_user_statuses(self):
        """
        Обновление статусов пользователей, если истек срок действия ключей.
        """
        users = await UserCl.get_all_users()
        for user in users:
            try:
                for server in user.servers:
                    date_key_off = await server.date_key_off.get()
                    if date_key_off:
                        expiration_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
                        if expiration_date < datetime.now():
                            await server.status_key.set("blocked")
            except Exception as e:
                logging.error(f"Ошибка при обновлении статуса пользователя {user.chat_id}: {e}")

    async def send_logs_to_admin(self):
        """
        Отправка логов администраторам.
        """
        log_files = ["/var/log/pingi_vpn_bot_output.log", "/var/log/pingi_vpn_bot_error.log"]
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "rb") as file:
                        await self.bot.send_document(chat_id=ADMIN_CHAT_IDS[0], document=file, caption=f"Логи: {log_file}")
                except Exception as e:
                    logging.error(f"Ошибка при отправке логов: {e}")

    async def execute_daily_tasks(self):
        """
        Выполняет все ежедневные задачи:
        1. Генерация и отправка статистики.
        2. Обновление данных рефералов.
        3. Обновление статусов пользователей.
        4. Отправка логов администраторам.
        """
        try:
            await self.show_statistic()
            #await self.update_user_statuses()
            #await self.send_logs_to_admin()
        except Exception as e:
            logging.error(f"Ошибка при выполнении ежедневных задач: {e}")
