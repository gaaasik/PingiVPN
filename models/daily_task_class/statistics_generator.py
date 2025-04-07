import logging
import os
from datetime import datetime, timedelta
import aiofiles
from redis_configs.redis_settings import redis_client_main
from models.UserCl import UserCl
import communication_with_servers.result_processor.all_processor.result_creating_user as result_module



async def generate_statistic_text(date: datetime = None) -> str:
    """
    Генерирует текст статистики за указанную дату.
    Если дата не передана, используется вчерашний день.
    """
    try:
        if not date:
            date = datetime.now() - timedelta(days=1)

        # Собираем данные статистики
        new_users = await UserCl.count_users_by_date(date) or 0
        total_users = len(await UserCl.get_all_users()) or 0
        active_users = await UserCl.count_active_chat_users() or 0
        paid_users = await UserCl.count_paid_users_by_date(date) or 0
        total_paid_users = await UserCl.count_total_paid_users(datetime(2024, 11, 24)) or 0
        remaining_configs = await get_remaining_configs() or 0
        count_vless = result_module.daily_created_users_vless
        count_wg = result_module.daily_created_users_wg
        remaining_urls = await count_remaining_vless_links() or 0

        # Формируем текст статистики
        stats_message = (
            f"📊 <b>Статистика за {date.strftime('%d.%m.%Y')}</b> 📊\n\n"
            f"👥 <b>Новых пользователей:</b> {new_users}\n"
            f"🟢 <b>Активных чатов:</b> {active_users}\n"
            f"🌍 <b>Всего пользователей:</b> {total_users}\n"
            f"💳 <b>Оплатили за день:</b> {paid_users}\n"
            f"💳 <b>Всего оплат с 24.11.2024:</b> {total_paid_users}\n"
            f"🔑 <b>Осталось конфигураций:</b> {remaining_configs}\n"
            f"🔗 <b>Осталось ссылок Vless:</b> {remaining_urls}\n"
            f"🔄 <b>Сгенерировано новых ссылок Vless:</b> {count_vless}\n"
            f"🔄 <b>Сгенерировано новых файлов WG:</b> {count_wg}\n"
        ).strip()

        return stats_message if stats_message else f"❌ Статистика за {date.strftime('%d.%m.%Y')} недоступна"

    except Exception as e:
        logging.error(f"Ошибка при генерации статистики: {e}")
        return f"❌ Ошибка при генерации статистики за {date.strftime('%d.%m.%Y')}:\n<code>{str(e)}</code>"

async def count_remaining_vless_links() -> int:
    """
    Подсчитывает количество оставшихся Vless ссылок в файле.
    """
    try:
        configs_dir = os.getenv("CONFIGS_DIR", "C:/PycharmProjects/PingiVPN/configs")
        vless_file_path = os.path.join(configs_dir, "url_vless_new")

        if not os.path.exists(vless_file_path):
            logging.error(f"Файл {vless_file_path} не найден.")
            return 0

        async with aiofiles.open(vless_file_path, "r", encoding="utf-8") as file:
            links = [line.strip() for line in await file.readlines() if line.strip().startswith("vless://")]

        return len(links)

    except Exception as e:
        logging.error(f"Ошибка при чтении файла Vless: {e}")
        return 0

async def get_remaining_configs() -> int:
        """
        Возвращает количество оставшихся конфигурационных файлов.
        """
        try:
            # Приводим путь к стандартному виду для ОС (в Windows заменяет обратные слеши)

            from bot.utils.file_sender import BASE_CONFIGS_DIR
            directory = os.path.normpath(BASE_CONFIGS_DIR)

            # Проверяем, существует ли директория
            if not os.path.exists(directory):
                raise FileNotFoundError(f"Директория {directory} не найдена.")

            # Проверяем, является ли путь директорией
            if not os.path.isdir(directory):
                raise NotADirectoryError(f"{directory} не является директорией.")

            # Выводим содержимое директории для проверки
            files_in_directory = os.listdir(directory)
            # print(f"Содержимое директории {directory}: {files_in_directory}")

            # Считаем файлы с нужными расширениями
            conf_files = len([f for f in files_in_directory if f.endswith('_free.conf')])
            return conf_files  # Примерное значение для тестирования
        except FileNotFoundError as e:
            logging.error(f"Ошибка при подсчете фалов: {e}")
            return -1  # Возвращаем 0, если директория не найдена


