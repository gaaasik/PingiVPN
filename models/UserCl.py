import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
import aiosqlite
import json
from dotenv import load_dotenv
from models.ServerCl import ServerCl
import re

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))


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
        await self.user._update_field_in_db(self.name, new_value)

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



    async def get(self):
        if self.name == "is_subscribed_on_channel":
            return await self.user.check_subscription_channel
        return self.value


class UserCl:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_name = Field('user_name', "", self)
        self.registration_date = Field('registration_date', None, self)
        self.referral_old_chat_id = Field('referral_old_chat_id', 0, self)
        self.device = Field('device', "", self)
        self.is_subscribed_on_channel = Field('is_subscribed_on_channel', 0, self)
        self.days_since_registration = Field('days_since_registration', 0, self)
        self.email = Field('count_key', "", self)
        self.servers: list[ServerCl]  # Явное указание типа поля servers  # Поле для хранения списка серверов (список объектов Server_cl)
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
        return self


    async def add_server_json(self, server_params: dict):
        """Добавление нового сервера в JSON формате"""
        # Преобразуем параметры в объект Server_cl и добавляем его в список servers
        new_server = ServerCl(server_params, self)
        self.servers.append(new_server)


        # Обновляем поле value_key (список серверов) и count_key в базе данных
        await self._update_servers_in_db()

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

    @classmethod
    async def add_user_to_database(cls, chat_id: int, user_name: str, referral_old_chat_id: Optional[int] = 0):
        """Добавляет нового пользователя в базу данных"""
        self = cls(chat_id)
        # Проверка подписки пользователя на канал
        from bot_instance import bot
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
                    print(f"Пользователь {user_name} добавлен в таблицу users.")

                # Проверка существования записи в таблице users_key
                query_check_user_key = "SELECT chat_id FROM users_key WHERE chat_id = ?"
                async with db.execute(query_check_user_key, (self.chat_id,)) as cursor:
                    result_user_key = await cursor.fetchone()
                    if result_user_key:
                        print(f"Запись с chat_id {await self.user_name.get()} уже существует в таблице users_key.")
                    else:
                        query_add_user_key = """
                        INSERT INTO users_key (chat_id, count_key, value_key)
                        VALUES (?, ?, ?)
                        """
                        await db.execute(query_add_user_key, (self.chat_id, 0, ""))
                        print(f"Пользователь {user_name} добавлен в таблицу users_key.")

                # Подтверждаем все изменения
                await db.commit()

                # Устанавливаем значения user_name, registration_date и referral_old_chat_id через set()
                await self.user_name.set(user_name)
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await self.registration_date.set(current_date)
                await self.referral_old_chat_id.set(referral_old_chat_id)
                await self.check_subscription_channel()
                await self.days_since_registration.set(0)
                self.count_key.value = 0

                print(f"Все изменения для пользователя {user_name} с chat_id {self.chat_id} сохранены в базе.")
                return True  # Успешное добавление
        except Exception as e:
            print(f"Ошибка при добавлении пользователя в базу данных: {e}")
            return False

    async def add_key_vless(self):
        """Создает сервер VLESS с фиксированными параметрами, используя первый доступный URL и добавляет его в список серверов пользователя."""
        free_day = 3  # Количество бесплатных дней
        current_date = datetime.now()

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
        server_params = self._generate_server_params(current_date, url_vless, free_day)

        # Создание нового сервера и обновление базы данных
        await self.add_server_json(server_params)
        print(f"Сервер VLESS добавлен для пользователя с chat_id {self.chat_id}")
        return True

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

            print(f"Осталось {len(remaining_urls)} доступных URL для VLESS.")
            return url_vless

        except Exception as e:
            print(f"Ошибка при работе с файлами URL: {e}")
            return None

    def _generate_server_params(self, current_date, url_vless, free_day):
        """Генерирует параметры нового сервера VLESS, извлекая информацию из URL."""

        # Извлечение uuid, server_ip и name_key из URL
        uuid_match = re.search(r'vless://([a-f0-9\-]+)@', url_vless)
        server_ip_match = re.search(r'@([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):', url_vless)
        name_key_match = re.search(r'#([^ ]+)', url_vless)
        country_match = re.search(r'_([A-Za-z]+)$', url_vless)

        uuid_id = uuid_match.group(1) if uuid_match else ""
        server_ip = server_ip_match.group(1) if server_ip_match else ""
        name_key = name_key_match.group(1).replace("Vless-", "") if name_key_match else ""
        #name_key = name_key_match.group(1) if name_key_match else ""
        country_server = country_match.group(1) if country_match else "Unknown"

        return {
            "name_protocol": "vless",
            "email_key": name_key,
            "uuid_id": uuid_id,
            "name_server": f"VLESS Server {server_ip}",
            "country_server": country_server,
            "server_ip": server_ip,
            "name_key_for_user": name_key,
            "user_ip": "",  # Уникальный IP
            "name_conf": "vless_config",
            "enable": True,
            "vpn_usage_start_date": current_date.strftime("%Y-%m-%d %H:%M:%S"),
            "traffic_up": 0,
            "traffic_down": 0,
            "has_paid_key": 0,
            "status_key": "key_free",
            "is_notification": False,
            "days_after_pay": 30,
            "date_payment_key": current_date.strftime("%Y-%m-%d %H:%M:%S"),
            "date_expire_of_paid_key": (current_date.replace(year=current_date.year + 1)).strftime("%Y-%m-%d %H:%M:%S"),
            "date_creation_key": current_date.strftime("%Y-%m-%d %H:%M:%S"),
            "date_expire_free_trial": (current_date + timedelta(days=free_day)).strftime("%Y-%m-%d %H:%M:%S"),
            "url_vless": url_vless
        }






    async def _load_user_data(self):
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT chat_id, user_name, registration_date, referral_old_chat_id, device, 
                   is_subscribed_on_channel, days_since_registration, email
            FROM users
            WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    # Извлекаем данные из базы
                    (chat_id, user_name, registration_date, referral_old_chat_id,
                     device, is_subscribed_on_channel, days_since_registration,
                     email) = result

                    # Устанавливаем значения через `set` для сохранения типа `Field`
                    self.user_name.value = user_name
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
            SELECT value_key, count_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    value_key, load_count_key = result
                    self.count_key.value = load_count_key
                    if value_key:
                        try:
                            servers_data = json.loads(value_key)
                            # Преобразуем каждый сервер в объект Server_cl
                            if isinstance(servers_data, list):
                                self.servers = [ServerCl(server, self) for server in servers_data]
                            elif isinstance(servers_data, dict):  # На случай если value_key хранит один объект
                                self.servers = [ServerCl(servers_data, self)]
                            else:
                                self.servers = []
                        except json.JSONDecodeError:
                            print(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                    else:
                        self.servers = []  # Если value_key пуст, значит серверов нет
                else:
                    print(f"Нет серверов для пользователя с chat_id {self.chat_id}")
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

    async def _update_field_in_db(self, field_name, value):
        """Обновление любого поля в базе данных с проверкой на наличие chat_id."""
        async with aiosqlite.connect(database_path_local) as db:
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
