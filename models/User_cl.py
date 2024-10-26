import os
from datetime import datetime
from pathlib import Path
import aiosqlite
import json
from dotenv import load_dotenv
from models.Server_cl import Server_cl

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))


class Field_cl:
    def __init__(self, name, value, user):
        self.name = name  # Название поля (например, 'user_name')
        self.value = value  # Текущее значение поля
        self.user = user  # Ссылка на объект User

    async def set(self, new_value):
        self.value = new_value
        setattr(self.user, f"_{self.name}", new_value)
        await self.user._update_field_in_db(self.name, new_value)



    def get(self):
        return self.value


class User_cl:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_name = ""
        self.registration_date = None
        self.referral_old_chat_id = 0
        self.device = ""
        self.is_subscribed_on_channel = None
        self.days_since_registration = None
        self.email = None
        self.servers: list[Server_cl]  # Явное указание типа поля servers  # Поле для хранения списка серверов (список объектов Server_cl)
        self.count_key = 0  # Поле для хранения количества серверов

    @classmethod
    async def create(cls, chat_id: int):
        self = cls(chat_id)
        await self.load_user_data()  # Загружаем данные пользователя
        await self.load_servers()  # Загружаем сервера
        return self

    async def load_user_data(self):
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
                    (self.chat_id, self.user_name, self.registration_date, self.referral_old_chat_id,
                     self.device, self.is_subscribed_on_channel, self.days_since_registration,
                     self.email) = result

                    # Создаем объекты Field для всех полей
                    self.user_name = Field_cl('user_name', self.user_name, self)
                    self.is_subscribed_on_channel = Field_cl('is_subscribed_on_channel', self.is_subscribed_on_channel, self)
                    self.device = Field_cl('device', self.device, self)
                    self.email = Field_cl('email', self.email, self)
                    self.days_since_registration = Field_cl('days_since_registration', self.days_since_registration, self)

    async def load_servers(self):
        """Загрузка списка серверов для пользователя"""
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT value_key, count_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    value_key, self.count_key = result
                    if value_key:
                        try:
                            servers_data = json.loads(value_key)
                            # Преобразуем каждый сервер в объект Server_cl
                            if isinstance(servers_data, list):
                                self.servers = [Server_cl(server, self) for server in servers_data]
                            elif isinstance(servers_data, dict):  # На случай если value_key хранит один объект
                                self.servers = [Server_cl(servers_data, self)]
                            else:
                                self.servers = []
                        except json.JSONDecodeError:
                            print(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                    else:
                        self.servers = []  # Если value_key пуст, значит серверов нет
                else:
                    print(f"Нет серверов для пользователя с chat_id {self.chat_id}")
                    self.servers = []

    async def add_server(self, server_params: dict):
        """Добавление нового сервера в JSON формате"""
        # Преобразуем параметры в объект Server_cl и добавляем его в список servers
        new_server = Server_cl(server_params, self)
        self.servers.append(new_server)
        self.count_key += 1  # Увеличиваем количество серверов

        # Обновляем поле value_key (список серверов) и count_key в базе данных
        await self._update_servers_in_db()

    async def _update_servers_in_db(self):
        """Обновление списка серверов и количества серверов в базе данных"""
        # Преобразуем каждый сервер обратно в словарь перед сохранением в базу данных
        servers_data = [server.to_dict() for server in self.servers]
        value_key_json = json.dumps(servers_data)

        async with aiosqlite.connect(database_path_local) as db:
            query_update = """
            UPDATE users_key 
            SET value_key = ?, count_key = ? 
            WHERE chat_id = ?
            """
            await db.execute(query_update, (value_key_json, self.count_key, self.chat_id))
            await db.commit()

    async def _update_field_in_db(self, field_name, value):
        """Обновление любого поля в базе данных"""
        async with aiosqlite.connect(database_path_local) as db:
            query = f"UPDATE users SET {field_name} = ? WHERE chat_id = ?"
            await db.execute(query, (value, self.chat_id))
            await db.commit()

        # async def check_subscription_channel(chat_id):
        #     from bot_instance import bot
        #     status = await bot.get_chat_member("@pingi_hub", chat_id)
        #     if status.status in ["member", "administrator", "creator"]:
        #         return True
        #     return False

    async def add_user_to_database(self, chat_id, user_name, referral_old_chat_id):
        """Добавляет нового пользователя в базу данных"""

        # Устанавливаем значения user_name и registration_date через set()
        await self.user_name.set(user_name)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.registration_date.set(current_date)
        await self.referral_old_chat_id.set(referral_old_chat_id)


        async with aiosqlite.connect(database_path_local) as db:
            # Проверка, существует ли пользователь в таблице users
            query_check_user = "SELECT chat_id FROM users WHERE chat_id = ?"
            async with db.execute(query_check_user, (self.chat_id,)) as cursor:
                result_user = await cursor.fetchone()
                if result_user:
                    print(f"Пользователь с chat_id {self.chat_id} уже существует в таблице users.")
                else:
                    query_add_user = """
                    INSERT INTO users (chat_id, user_name, registration_date, referral_old_chat_id, device, 
                                       is_subscribed_on_channel, days_since_registration, email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    await db.execute(query_add_user, (
                        self.chat_id,
                        self.user_name.get(),
                        self.registration_date.get(),
                        self.referral_old_chat_id,
                        self.device,
                        self.is_subscribed_on_channel,
                        self.days_since_registration,
                        self.email
                    ))
                    print(f"Пользователь {user_name} добавлен в таблицу users.")

            query_check_user_key = "SELECT chat_id FROM users_key WHERE chat_id = ?"
            async with db.execute(query_check_user_key, (self.chat_id,)) as cursor:
                result_user_key = await cursor.fetchone()
                if result_user_key:
                    print(f"Запись с chat_id {self.chat_id} уже существует в таблице users_key.")
                else:
                    query_add_user_key = """
                    INSERT INTO users_key (chat_id, count_key, value_key)
                    VALUES (?, ?, ?)
                    """
                    await db.execute(query_add_user_key, (self.chat_id, 0, ""))  # count_key = 0 и value_key пустое
                    print(f"Пользователь {user_name} добавлен в таблицу users_key.")

            await db.commit()
            print(f"Все изменения для пользователя {user_name} с chat_id {self.chat_id} сохранены в базе.")
            return True  # Успешное добавление
