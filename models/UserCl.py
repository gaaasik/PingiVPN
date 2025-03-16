import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union, Dict

import aiofiles
import aiosqlite
import json
from dotenv import load_dotenv

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.country_server_data import get_json_country_server_data, get_name_server_by_ip, get_country_server_by_ip

from models.ServerCl import ServerCl
import re
import logging

from models.referral_class.ReferralCL import ReferralCl

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Field:
    def __init__(self, name, value, user):
        self.name = name  # Название поля (например, 'user_name')
        self.value = value  # Текущее значение поля
        self.user = user  # Ссылка на объект User

    async def set(self, new_value):
        if self.name == "count_key":
            print("нельзя менять coutn_key не изнутри класса")
            return
        self.value = new_value
        setattr(self.user, f"_{self.name}", new_value)
        await self.user._update_fild_in_db(self.name, new_value)

    async def _update_count_key(self):
        if self.name == "count_key":
            # Открываем соединение с базой данных
            async with aiosqlite.connect(database_path_local) as db:
                # Извлекаем поле value_key для пользователя из таблицы users_key
                query = "SELECT value_key FROM users_key WHERE chat_id = ?"
                async with db.execute(query, (self.user.chat_id,)) as cursor:
                    result = await cursor.fetchone()
                    if result and result[0]:
                        # Загружаем JSON данных серверов из поля value_key
                        servers_data = json.loads(result[0])
                        # Подсчитываем количество серверов
                        new_value = len(servers_data) if isinstance(servers_data, list) else 0
                    else:
                        new_value = 0  # Если value_key пуст, значение count_key = 0

                # Обновляем значение count_key в классе и базе данных
                self.value = new_value
                setattr(self.user, f"_{self.name}", new_value)
                await self.user._update_count_key_in_db(self.name, new_value)
                return new_value

    async def get_date(self):
        # Проверяем, можно ли использовать данный метод для текущего поля
        if self._name not in ["date_key_off", "date_creation_key", "date_payment_key"]:
            raise AttributeError(f"Метод get_date не может быть использован для поля '{self._name}'")

        # Преобразуем строку в datetime и возвращаем только дату
        if isinstance(self._value, str):
            date_obj = datetime.strptime(self._value, "%d.%m.%Y %H:%M:%S")
        elif isinstance(self._value, datetime):
            date_obj = self._value
        else:
            raise ValueError("Неправильный формат даты")

        return date_obj.strftime("%d.%m.%Y")

    async def _update_days_since_registration(self):
        if self.name == "days_since_registration":
            registration_date_value = await self.user.registration_date.get()

            if not registration_date_value:
                print("Дата регистрации не установлена.")
                return

            registration_date = datetime.strptime(registration_date_value, "%d.%m.%Y %H:%M:%S")

            current_date = datetime.now()
            days_since_registration = (current_date - registration_date).days
            await self.user.days_since_registration.set(days_since_registration)
            return days_since_registration

    async def get(self):
        if self.name == "days_since_registration":
            return await self._update_days_since_registration()
        if self.name == "count_key":
            return await self._update_count_key()
        if self.name == "is_subscribed_on_channel":
            return await self.user.check_subscription_channel()
        return self.value


class UserCl:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_name_full = Field('user_name_full', "", self)
        self.user_login = Field('user_login', "", self)
        self.registration_date = Field('registration_date', None, self)
        self.referral_old_chat_id = Field('referral_old_chat_id', 0, self)
        self.device = Field('device', "", self)
        self.is_subscribed_on_channel = Field('is_subscribed_on_channel', 0, self)
        self.days_since_registration = Field('days_since_registration', 0, self)
        self.email = Field('email', "", self)
        self.servers: list[ServerCl]  # Явное указание типа поля servers  # Поле для хранения списка серверов (список объектов Server_cl)
        self.active_server: ServerCl = None
        self.history_key_list: list[ServerCl]
        self.count_key = Field('count_key', 0, self)  # Поле для хранения количества серверов

    @classmethod
    async def load_user(cls, chat_id: int) -> Optional["UserCl"]:
        self = cls(chat_id)

        async with aiosqlite.connect(database_path_local) as db:
            query = "SELECT 1 FROM users WHERE chat_id = ?"
            async with db.execute(query, (chat_id,)) as cursor:
                result = await cursor.fetchone()
                if not result:
                    print(f"Пользователь с chat_id {chat_id} не найден в базе данных.")
                    return None

        user_data_loaded = await self._load_user_data()
        if not user_data_loaded:
            return None

        await self._load_servers()  # Загружаем сервера
        await self.choosing_working_server()

        return self

    @classmethod
    async def add_user_to_database(cls, chat_id: int, user_name_full: str, user_login: str,
                                   referral_old_chat_id: Optional[int] = 0):
        """Добавляет нового пользователя в базу данных"""
        self = cls(chat_id)
        # Проверка подписки пользователя на канал
        try:
            async with aiosqlite.connect(database_path_local) as db:
                # Проверка существования пользователя в таблице users
                query_check_user = "SELECT chat_id FROM users WHERE chat_id = ?"
                async with db.execute(query_check_user, (self.chat_id,)) as cursor:
                    result_user = await cursor.fetchone()
                    if result_user:
                        print(f"Пользователь с chat_id {self.chat_id} уже существует в таблице users.")
                        return False  # Прерывание, если пользователь существует

                    # Добавляем запись в таблицу users, если пользователя нет
                    query_add_user = """
                    INSERT INTO users (chat_id)
                    VALUES (?)
                    """
                    await db.execute(query_add_user, (self.chat_id,))
                    print(f"Пользователь {user_name_full} добавлен в таблицу users.")

                # Проверка существования записи в таблице users_key
                query_check_user_key = "SELECT chat_id FROM users_key WHERE chat_id = ?"
                async with db.execute(query_check_user_key, (self.chat_id,)) as cursor:
                    result_user_key = await cursor.fetchone()
                    if result_user_key:
                        print(f"Запись с chat_id {await self.user_name_full.get()} уже существует в таблице users_key.")
                    else:
                        query_add_user_key = """
                        INSERT INTO users_key (chat_id, count_key, value_key)
                        VALUES (?, ?, ?)
                        """
                        await db.execute(query_add_user_key, (self.chat_id, 0, ""))
                        print(f"Пользователь {user_name_full} добавлен в таблицу users_key.")

                # Подтверждаем все изменения
                await db.commit()

                # Устанавливаем значения user_name, registration_date и referral_old_chat_id через set()
                await self.user_name_full.set(user_name_full)
                await self.user_login.set(user_login)
                current_date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                await self.registration_date.set(current_date)
                await self.referral_old_chat_id.set(referral_old_chat_id)
                await self.check_subscription_channel()
                await self.days_since_registration.set(0)
                self.count_key.value = 0

                print(f"Все изменения для пользователя {user_name_full} с chat_id {self.chat_id} сохранены в базе.")
                return True  # Успешное добавление
        except Exception as e:
            print(f"Ошибка при добавлении пользователя в базу данных: {e}")
            return False

    @classmethod
    async def get_all_users(cls) -> list:
        """Возвращает список всех пользователей (chat_id) из базы данных."""
        user_ids = []
        try:
            async with aiosqlite.connect(database_path_local) as db:
                query = "SELECT chat_id FROM users"
                async with db.execute(query) as cursor:
                    user_ids = [row[0] for row in await cursor.fetchall()]

        except Exception as e:
            print(f"Ошибка при получении всех пользователей: {e}")
        return user_ids

    @classmethod
    async def count_users_by_date(cls, date: datetime) -> int:
        """
        Подсчитывает количество пользователей, зарегистрированных в указанную дату.
        """
        try:
            async with aiosqlite.connect(database_path_local) as db:
                # SQL-запрос для подсчета пользователей по дате
                query = """
                SELECT COUNT(*) FROM users 
                WHERE DATE(substr(registration_date, 7, 4) || '-' || substr(registration_date, 4, 2) || '-' || substr(registration_date, 1, 2)) = ?
                """

                # Преобразуем дату в формат YYYY-MM-DD
                date_str = date.strftime("%Y-%m-%d")

                # Логируем дату и запрос
                logging.info(f"Выполняется подсчет пользователей за дату: {date_str}")
                logging.info(f"SQL-запрос: {query}")

                # Выполняем запрос
                async with db.execute(query, (date_str,)) as cursor:
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    return count

        except Exception as e:
            # Логируем ошибку
            logging.error(f"Ошибка при подсчете пользователей за дату {date}: {e}")
            return 0

    @classmethod
    async def count_paid_users_by_date(cls, date: datetime) -> int:
        """
        Подсчитывает количество пользователей, которые оплатили подписку за указанную дату.
        """
        try:
            async with aiosqlite.connect(database_path_local) as db:
                query = """
                SELECT COUNT(DISTINCT chat_id) 
                FROM payments 
                WHERE status = 'payment.succeeded' 
                AND DATE(created_at) = DATE(?)
                """
                date_str = date.strftime("%Y-%m-%d")
                async with db.execute(query, (date_str,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logging.error(f"Ошибка при подсчете оплаченных пользователей за дату {date}: {e}")
            return 0

    @classmethod
    async def count_total_paid_users(cls, start_date: datetime) -> int:
        """
        Подсчитывает общее количество успешных оплат, начиная с определенной даты.
        """
        try:
            async with aiosqlite.connect(database_path_local) as db:
                query = """
                SELECT COUNT(chat_id) 
                FROM payments 
                WHERE status = 'payment.succeeded' 
                AND DATE(created_at) >= DATE(?)
                """
                start_date_str = start_date.strftime("%Y-%m-%d")
                async with db.execute(query, (start_date_str,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logging.error(f"Ошибка при подсчете всех оплаченных пользователей с {start_date}: {e}")
            return 0

    @staticmethod
    async def user_exists(chat_id: int) -> bool:
        """
        Проверяет, существует ли пользователь с указанным chat_id.
        """
        try:
            user = await UserCl.load_user(chat_id)
            return user is not None
        except Exception as e:
            logging.error(f"Ошибка при проверке существования пользователя {chat_id}: {e}")
            return False

    async def choosing_working_server(self):
        """Выбирает активный сервер из списка серверов пользователя."""
        if await self.count_key.get() <= 0:
            self.active_server = None
            return
        for sample in self.servers:
            if await sample.status_key.get() == "active" or await sample.status_key.get() == "free_key":  # Используем await
                self.active_server = sample  # Присваиваем сервер, а не его статус
                await self.active_server.status_key.set("active")
                return  # Завершаем поиск, как только нашли активный сервер
        self.active_server = None  # Если активный сервер не найден

    async def add_server_json(self, server_params: dict):
        """Добавление нового сервера в JSON формате"""
        # Преобразуем параметры в объект Server_cl и добавляем его в список servers
        if server_params:
            new_server = ServerCl(server_params, self)
            self.servers.append(new_server)

            # Обновляем поле value_key (список серверов) и count_key в базе данных
            await self.push_field_json_in_db("servers")
            #await self._update_servers_in_db()
            await self.count_key._update_count_key()

    async def check_subscription_channel(self, channel_username="@pingi_hub"):
        """
        Проверяет, подписан ли пользователь на указанный канал.
        :param channel_username: Имя пользователя канала в Telegram (по умолчанию "@pingi_hub").
        :return: True, если пользователь подписан на канал; иначе False.
        """

        from bot_instance import bot  # Импорт бота, если он не передан напрямую
        try:

            status = await bot.get_chat_member(channel_username, self.chat_id)
            if status.status in ["member", "administrator", "creator"]:
                await self.is_subscribed_on_channel.set(1)
                return True
            await self.is_subscribed_on_channel.set(0)
            return False

        except Exception as e:
            print(f"Ошибка при проверке подписки на канал: {e}")
            # Если произошла ошибка, поле is_subscribed_on_channel остается неизменным или устанавливается в 0.
            await self.is_subscribed_on_channel.set(0)
            return False

    async def add_key_vless(self, free_day=7):

        """Создает сервер VLESS с фиксированными параметрами, используя первый доступный URL и добавляет его в список серверов пользователя."""

        # Определение путей к файлам
        project_root = Path(__file__).resolve().parent.parent
        url_vless_new_path = project_root / "configs" / "url_vless_new"
        url_vless_user_path = project_root / "configs" / "url_vless_user"

        # Асинхронное чтение URL из файла
        url_vless = await self._get_first_available_url(url_vless_new_path, url_vless_user_path)
        if not url_vless:
            print("Нет доступных URL для VLESS.")
            return False

        # Параметры нового сервера VLESS
        server_params = await self.generate_server_params_vless(url_vless, free_day)

        #Если был активный ключ мы его блокируем
        if self.active_server:
            await self.active_server.status_key.set("blocked")

        # Создание нового сервера и обновление базы данных
        await self.add_server_json(server_params)
        print(f"Сервер VLESS добавлен для пользователя с chat_id {self.chat_id}")
        # Проверяем реферала и начисляем бонус, если нужно
        try:
            await ReferralCl.add_referral_bonus(self.chat_id)
        except Exception as e:
            await send_admin_log(bot, f"❌ Ошибка при начислении бонуса за реферала {self.chat_id}: {e}")
            logging.error(f"❌ Ошибка при начислении бонуса за реферала {self.chat_id}: {e}")
        #Теперь новый active_server
        await self.choosing_working_server()
        return True

    async def add_key_wireguard(self, json_with_wg=None, free_day=7):

        if not await self.count_key.get():
            server_params = await self._generate_server_params_wireguard(json_with_wg, free_day)
            await self.add_server_json(server_params)

            # Создание нового сервера и обновление базы данных
            print(f"Сервер WireGuard добавлен для пользователя с hat_id {self.chat_id}")
        await self.choosing_working_server()

    async def check_file_PINGI(self) -> Union[str, bool]:
        user_login = await self.user_login.get()
        chat_id = self.chat_id

        # Проверяем переменную окружения CONFIGS_DIR
        CONFIGS_DIR = os.getenv('CONFIGS_DIR')
        if not CONFIGS_DIR:
            raise ValueError("CONFIGS_DIR не задана в переменных окружения.")

        # Определяем путь для директории зарегистрированных пользователей
        REGISTERED_USERS_DIR = os.path.join(CONFIGS_DIR, 'registered_user')
        if not os.path.exists(REGISTERED_USERS_DIR):
            os.makedirs(REGISTERED_USERS_DIR)
            print(f"Создана директория для зарегистрированных пользователей: {REGISTERED_USERS_DIR}")

        # Определяем директорию пользователя
        folder_name = f"{chat_id}_{user_login}" if user_login else f"{chat_id}"
        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            print(f"Создана новая папка для пользователя: {user_dir}")

        # Проверяем наличие файлов конфигурации и QR-кода
        config_file_path = os.path.join(user_dir, "PingiVPN.conf")
        qr_code_path = os.path.join(user_dir, "PingiVPN.png")

        missing_files = []
        if not os.path.exists(config_file_path):
            missing_files.append("PingiVPN.conf")
        if not os.path.exists(qr_code_path):
            missing_files.append("PingiVPN.png")

        if missing_files:
            print(f"Отсутствуют файлы: {', '.join(missing_files)} в папке {user_dir}.")
            return False

        print(f"Все необходимые файлы присутствуют в {user_dir}.")
        return config_file_path

    async def _get_first_available_url(self, new_path, used_path):
        """Получает первый доступный URL из файла, перемещает его в использованные и возвращает URL."""
        try:
            async with aiofiles.open(new_path, "r") as file:
                urls = await file.readlines()

            if not urls:
                return None

            url_vless = urls[0].strip()
            remaining_urls = urls[1:]

            # Запись оставшихся URL и обновление использованных
            async with aiofiles.open(new_path, "w") as file:
                await file.writelines(remaining_urls)

            async with aiofiles.open(used_path, "a") as file:
                await file.write(url_vless + "\n")

            #сообщение админу
            await send_admin_log(bot,
                                 f"Добавлен пользователь {self.chat_id}, {await self.user_login.get()}. Осталось {len(remaining_urls)} ключей vless ")
            logging.info(f"Осталось {len(remaining_urls)} доступных URL для VLESS.")
            return url_vless

        except Exception as e:
            print(f"Ошибка при работе с файлами URL: {e}")
            return None

    async def _get_server_name_by_ip(self, server_data, ip_address: str) -> str:
        """Получает имя сервера по его IP."""
        print("server_data", server_data)
        for server in server_data.get("servers", []):
            if server.get("address") == ip_address:
                return server.get("name", "Unknown_Server")
        return "Unknown_Server"

    async def generate_server_params_vless(self, url_vless, free_day):

        """Генерирует параметры нового сервера VLESS, извлекая информацию из URL."""
        current_date = datetime.now()

        # Извлечение uuid, server_ip и name_key из URL
        uuid_match = re.search(r'vless://([a-f0-9\-]+)@', url_vless)
        server_ip_match = re.search(r'@([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):', url_vless)
        name_key_match = re.search(r'#([^ ]+)', url_vless)
        country_match = re.search(r'_([A-Za-z]+)$', url_vless)

        uuid_id = uuid_match.group(1) if uuid_match else ""
        server_ip = server_ip_match.group(1) if server_ip_match else ""
        email_key = name_key_match.group(1).replace("Vless-", "") if name_key_match else ""
        name_key = name_key_match.group(1).replace("Vless-", "").rpartition('_')[0] if name_key_match else ""
        country_server = country_match.group(1) if country_match else "Unknown"
        name_server = await get_name_server_by_ip(server_ip)

        return {
            "country_server": country_server,
            "date_creation_key": current_date.strftime("%d.%m.%Y %H:%M:%S"),
            "date_key_off": (current_date + timedelta(days=free_day)).strftime("%d.%m.%Y %H:%M:%S"),
            "date_payment_key": "0",
            "date_latest_handshake": "0",
            "email_key": email_key,
            "enable": True,
            "has_paid_key": 0,
            "name_key": f"{name_key}",
            "name_protocol": "vless",
            "name_server": f"{name_server}",
            "server_ip": server_ip,
            "status_key": "active",
            "traffic_down": 0,
            "traffic_up": 0,
            "url_vless": url_vless,
            "uuid_id": uuid_id,
        }

    async def _generate_server_params_wireguard(self, json_with_wg, free_day: int):

        """Генерирует параметры нового сервера WireGuard, извлекая информацию из конфигурационного файла."""
        try:
            current_date = datetime.now()
            # Инициализируем переменные для данных
            private_key = None
            address = None
            endpoint = None
            if json_with_wg:
                logging.info(
                    f"Начало работы функции _generate_server_params_wireguard. c json {json_with_wg}")
                server_ip = json_with_wg.get("server_ip")
                user_ip = json_with_wg.get("user_ip")
            else:

                config_file_path = await self.check_file_PINGI()
                if not config_file_path:
                    logging.error("Ошибка с путем к конфигурациям config_file_path")
                    return
                logging.info(
                    f"Начало работы функции _generate_server_params_wireguard. Путь к файлу: {config_file_path}")
                # Преобразуем путь в объект Path для удобной работы
                config_file_path = Path(config_file_path)
                logging.debug(f"Обработанный путь к конфигурационному файлу: {config_file_path}")

                # Проверяем, существует ли файл
                if not config_file_path.exists():
                    logging.error(f"Файл конфигурации не найден: {config_file_path}")
                    raise FileNotFoundError(f"Файл конфигурации не найден: {config_file_path}")

                # Читаем содержимое конфигурационного файла
                logging.info(f"Открываем файл: {config_file_path}")
                with config_file_path.open('r', encoding='utf-8') as file:
                    lines = file.readlines()

                logging.debug(f"Файл прочитан. Количество строк: {len(lines)}")

                # Парсим файл построчно
                for line in lines:
                    line = line.strip()
                    logging.debug(f"Обработка строки: {line}")

                    if line.startswith("PrivateKey"):
                        private_key = line.split("=")[1].strip()
                        logging.info(f"Найден PrivateKey: {private_key}")
                    elif line.startswith("Address"):
                        address = line.split("=")[1].strip()
                        logging.info(f"Найден Address: {address}")
                    elif line.startswith("Endpoint"):
                        endpoint = line.split("=")[1].strip()
                        logging.info(f"Найден Endpoint: {endpoint}")

                # Извлекаем server_ip из Endpoint
                server_ip = endpoint.split(":")[0] if endpoint else None
                user_ip = address.split("/")[0] if address else None

                logging.debug(f"Извлечён server_ip: {server_ip}, user_ip: {user_ip}")

                # Проверяем, что все необходимые данные извлечены
                if not all([private_key, address, server_ip]):
                    logging.error("Некоторые данные из конфигурационного файла отсутствуют или некорректны.")
                    raise ValueError("Некоторые данные из конфигурационного файла отсутствуют или некорректны.")
            name_server = await get_name_server_by_ip(server_ip)
            country_server = await get_country_server_by_ip(server_ip)

            # Генерируем JSON с параметрами сервера
            name_key = f"WireGuard PingiVPN"  # Например, уникальное имя ключа
            logging.info("Генерация параметров сервера WireGuard завершена.")
            return {
                "country_server": country_server,
                "date_creation_key": current_date.strftime("%d.%m.%Y %H:%M:%S"),
                "date_key_off": (current_date + timedelta(days=free_day)).strftime("%d.%m.%Y %H:%M:%S"),
                "date_payment_key": "0",
                "date_latest_handshake": "0",
                "email_key": private_key,
                "enable": True,
                "has_paid_key": 0,
                "name_key": name_server,
                "name_protocol": "wireguard",
                "name_server": f"{name_server}",
                "server_ip": server_ip,
                "status_key": "active",
                "traffic_down": 0,
                "traffic_up": 0,
                "user_ip": user_ip,
                "uuid_id": "0",
            }

        except FileNotFoundError as e:
            logging.error(f"Файл не найден: {e}")
            raise
        except ValueError as e:
            logging.error(f"Ошибка обработки данных: {e}")
            raise
        except Exception as e:
            logging.exception(f"Непредвиденная ошибка: {e}")
            raise

    async def _load_user_data(self):
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT chat_id, user_name_full, user_login, registration_date, referral_old_chat_id, device, 
                   is_subscribed_on_channel, days_since_registration, email
            FROM users
            WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    # Извлекаем данные из базы
                    (chat_id, user_name_full, user_login, registration_date, referral_old_chat_id,
                     device, is_subscribed_on_channel, days_since_registration,
                     email) = result

                    # Устанавливаем значения через `set` для сохранения типа `Field`
                    self.user_name_full.value = user_name_full
                    self.user_login.value = user_login
                    self.registration_date.value = registration_date
                    self.referral_old_chat_id.value = referral_old_chat_id
                    self.device.value = device
                    self.is_subscribed_on_channel.value = is_subscribed_on_channel
                    self.days_since_registration.value = days_since_registration
                    self.email.value = email
                    return True
                else:
                    print(f"Пользователь с chat_id {self.chat_id} не найден в базе данных.")
                    return False  # Пользователь не найден

    async def _load_servers(self):
        """Загрузка списка серверов для пользователя"""
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT value_key, count_key, history_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    value_key, load_count_key, history_key = result
                    self.count_key.value = load_count_key

                    if value_key:
                        try:
                            servers_data = json.loads(value_key)
                            # Преобразуем каждый сервер в объект Server_cl
                            if isinstance(servers_data, list):
                                self.servers = [ServerCl(key, self) for key in servers_data]
                            elif isinstance(servers_data, dict):  # На случай если value_key хранит один объект
                                self.servers = [ServerCl(servers_data, self)]
                            else:
                                self.servers = []
                        except json.JSONDecodeError:
                            logging.error(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                    else:
                        self.servers = []  # Если value_key пуст, значит серверов нет

                    if history_key:
                        try:
                            history_key_data = json.loads(history_key)
                            # Преобразуем каждый сервер в объект Server_cl
                            if isinstance(history_key_data, list):
                                self.history_key_list = [ServerCl(key, self) for key in history_key_data]
                            elif isinstance(history_key_data, dict):  # На случай если history_key хранит один объект
                                self.history_key_list = [ServerCl(servers_data, self)]
                            else:
                                self.history_key_list = []
                        except json.JSONDecodeError:
                            logging.error(
                                f"Ошибка при парсинге history_key_list для пользователя с chat_id {self.chat_id}")
                    else:
                        self.history_key_list = []  # Если value_key пуст, значит серверов нет
                else:
                    logging.error(f"Нет серверов для пользователя с chat_id {self.chat_id}")
                    self.servers = []

    async def _update_servers_in_db(self):
        """Обновление списка серверов и количества серверов в базе данных"""
        # Преобразуем каждый сервер обратно в словарь перед сохранением в базу данных
        servers_data = [await server.to_dict() for server in self.servers]
        value_key_json = json.dumps(servers_data)

        async with aiosqlite.connect(database_path_local) as db:
            query_update = """
            UPDATE users_key 
            SET value_key = ?
            WHERE chat_id = ?
            """
            await db.execute(query_update, (value_key_json, self.chat_id))
            await db.commit()

    async def push_field_json_in_db(self, field_json: str):
        try:
            """Обновление списка серверов и количества серверов в базе данных"""
            if field_json == "history_key_list" or field_json == "history_key":
                push_variable = self.history_key_list
                push_field_in_db = "history_key"
            elif field_json == "servers" or field_json == "server"  or field_json == "value_key":
                push_variable = self.servers
                push_field_in_db = "value_key"
            else:
                logging.error("Не известное поле для обновления в базе данных, не понятно что обновлять")
                return
            # Преобразуем каждый сервер обратно в словарь перед сохранением в базу данных
            servers_data = [await key.to_dict() for key in push_variable]
            value_key_json = json.dumps(servers_data)

            async with aiosqlite.connect(database_path_local) as db:
                query_update = f"""
                        UPDATE users_key 
                        SET {push_field_in_db} = ?
                        WHERE chat_id = ?
                        """
                await db.execute(query_update, (value_key_json, self.chat_id))
                await db.commit()
        except Exception as e:
            logging.error(f"Ошибка при обновление поля в db: {e}")


    async def _update_fild_in_db(self, field_name, value):
        """Обновление любого поля в базе данных с проверкой на наличие chat_id."""
        async with aiosqlite.connect(database_path_local) as db:

            # Проверка на существование столбца
            query_check_column = "PRAGMA table_info(users)"
            async with db.execute(query_check_column) as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]  # Имя столбца во второй позиции

            if field_name not in column_names:
                print(f"В таблице 'users' отсутствует поле '{field_name}', поэтому база данных не обновлена!")
                return

            #сама запись в таблицу
            if field_name == "chat_id":
                # Проверка существования chat_id в таблице users
                query_check = "SELECT chat_id FROM users WHERE chat_id = ?"
                async with db.execute(query_check, (value,)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        print("Данный пользователь уже есть в базе данных, его нельзя менять.")
                        return
                    else:
                        # Добавление нового пользователя с только chat_id
                        query_add_user = "INSERT INTO users (chat_id) VALUES (?)"
                        await db.execute(query_add_user, (value,))
                        await db.commit()
                        print("Добавлен новый пользователь в базу данных.")
            else:
                # Обновление поля, если field_name не равен "chat_id"
                query = f"UPDATE users SET {field_name} = ? WHERE chat_id = ?"
                await db.execute(query, (value, self.chat_id))
                await db.commit()
                print(f"Поле '{field_name}' обновлено для пользователя с chat_id {self.chat_id}.")

    async def _update_count_key_in_db(self, field_name, value):
        """Обновление count_key в таблице users_key для текущего пользователя."""
        async with aiosqlite.connect(database_path_local) as db:
            if field_name == "count_key":
                query = "UPDATE users_key SET count_key = ? WHERE chat_id = ?"
                await db.execute(query, (value, self.chat_id))
                await db.commit()



    async def update_key_to_vless(self, url: str = ""):
        """
        Обновляет ключ пользователя на VLESS.
        - Отключает старый ключ.
        - Копирует старые данные в history_key_list.
        - Обновляет uuid_id, email_key, name_protocol, server_ip.
        - Оставляет даты создания и платежей прежними.
        """
        ############################## TEST ######################################################################
        if url == "":
            project_root = Path(__file__).resolve().parent.parent
            url_vless_new_path = project_root / "configs" / "url_vless_new"
            url_vless_user_path = project_root / "configs" / "url_vless_user"

            # Асинхронное чтение URL из файла
            url_vless = await self._get_first_available_url(url_vless_new_path, url_vless_user_path)
            if not url_vless:
                print("Нет доступных URL для VLESS.")
                return False
            url = url_vless
        ############################## TEST ######################################################################Ошибка при определении task_type:

        if self.active_server:
            current_date = datetime.now()

            # Получаем дату отключения ключа и конвертируем её из строки в datetime
            date_key_off_str = await self.active_server.date_key_off.get()
            date_key_off = datetime.strptime(date_key_off_str, "%d.%m.%Y %H:%M:%S")

            # Вычисляем оставшиеся дни
            free_day = (date_key_off - current_date).days + 1
            logging.info(f"высчитали количество дней до отключения = {free_day}")
            old_key_data = self.active_server

            self.servers.remove(old_key_data)
            logging.info("Удаляем старый ключ из servers, ")
            for server in self.servers:
                logging.error(f"Сейчас в server есть ключ, а его не должно быть, {server}")
            self.history_key_list.append(old_key_data)
            await self.push_field_json_in_db("history_key_list")
            logging.info(f"добавили старый ключ в поле history_key_list")
            await self.active_server.enable.set(False)
            logging.info(f"отключение старого ключа")

            new_key_params = await self.generate_server_params_vless(url, free_day)
            await self.add_server_json(new_key_params)
            # Теперь новый active_server
            await self.choosing_working_server()
            return True

        else:
            logging.info(f"Нет активных ключей, создаю новый ключ для chat_id == {self.chat_id}")

    async def update_key_to_wireguard(self, json_with_wg: Dict = None):
        """
        Обновляет ключ пользователя на VLESS.
        - Отключает старый ключ.
        - Копирует старые данные в history_key_list.
        - Обновляет uuid_id, email_key, name_protocol, server_ip.
        - Оставляет даты создания и платежей прежними.
        """
        ############################## TEST ######################################################################
        if not json_with_wg:
            logging.info("вызван ТЕСТОВЫЙ update_key_to_wireguard")
            json_with_wg = {
                "server_ip": "147.45.242.155",
                "user_ip": "10.8.0.5",
            }
        ############################## TEST ######################################################################

        if self.active_server:
            logging.info("вызван update_key_to_wireguard")
            current_date = datetime.now()

            # Получаем дату отключения ключа и конвертируем её из строки в datetime
            date_key_off_str = await self.active_server.date_key_off.get()
            date_key_off = datetime.strptime(date_key_off_str, "%d.%m.%Y %H:%M:%S")

            # Вычисляем оставшиеся дни
            free_day = (date_key_off - current_date).days
            logging.info(f"высчитали количество дней до отключения = {free_day + 1}")

            old_key_data = await self.active_server.to_dict()
            self.history_key_list.append(old_key_data)
            new_key_params = await self._generate_server_params_wireguard(json_with_wg, free_day)
            await self.active_server.enable.set(False)
            logging.info(f"отключение старого ключа")
            await self._update_history_key_in_db(old_key_data)
            #await self.active_server.delete()
            # Создание нового сервера и обновление базы данных Ошибка при обработке очереди
            await self.add_server_json(new_key_params)
            print(f"Сервер VLESS добавлен для пользователя с chat_id {self.chat_id}")

            # Теперь новый active_server
            await self.choosing_working_server()
            return True

        else:
            logging.info(f"Нет активных ключей, создаю новый ключ для chat_id == {self.chat_id}")
