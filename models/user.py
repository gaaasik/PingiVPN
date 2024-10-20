from datetime import datetime
from pathlib import Path
import aiosqlite
import json
from dotenv import load_dotenv
import os

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))


class Field:
    def __init__(self, name, value, user):
        self.name = name  # Название поля (например, 'user_name')
        self.value = value  # Текущее значение поля
        self.user = user  # Ссылка на объект User

    async def update_meaning(self, new_value):
        self.value = new_value
        setattr(self.user, f"_{self.name}", new_value)
        await self.user._update_field_in_db(self.name, new_value)

    def get(self):
        return self.value

class User:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_name = ""
        self.registration_date = None
        self.referrer_id = 0
        self.device = ""
        self.is_subscribed_on_channel = None
        self.days_since_registration = None
        self.email = None
        self.servers = []  # Поле для хранения списка серверов (из users_key)
        self.count_key = 0  # Поле для хранения количества серверов
        self.status_key = None  # Новое поле для хранения статуса ключа

    @classmethod
    async def create(cls, chat_id: int):
        self = cls(chat_id)
        await self.load_user_data()  # Загружаем данные пользователя
        await self.load_servers()  # Загружаем сервера и status_key
        return self

    async def load_user_data(self):
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT chat_id, user_name, registration_date, referrer_id, device, 
                   is_subscribed_on_channel, days_since_registration, email
            FROM users
            WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    (self.chat_id, self.user_name, self.registration_date, self.referrer_id,
                     self.device, self.is_subscribed_on_channel, self.days_since_registration,
                     self.email) = result

                    # Создаем объекты Field для всех полей
                    self.user_name = Field('user_name', self.user_name, self)
                    self.is_subscribed_on_channel = Field('is_subscribed_on_channel', self.is_subscribed_on_channel, self)
                    self.device = Field('device', self.device, self)
                    self.email = Field('email', self.email, self)
                    self.days_since_registration = Field('days_since_registration', self.days_since_registration, self)

    async def load_servers(self):
        """Загрузка списка серверов для пользователя и инициализация статуса ключа"""
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT value_key, count_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    value_key, self.count_key = result
                    try:
                        servers_data = json.loads(value_key)
                        self.servers = servers_data

                        # Инициализация поля status_key
                        if len(self.servers) > 0:
                            self.status_key = self.servers[0].get('status_key', 'new_user')  # Инициализируем status_key
                        else:
                            self.status_key = 'new_user'
                    except json.JSONDecodeError:
                        print(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                else:
                    print(f"Нет серверов для пользователя с chat_id {self.chat_id}")

    async def add_server(self, server_params: dict):
        """Добавление нового сервера в JSON формате"""
        self.servers.append(server_params)
        self.count_key += 1  # Увеличиваем количество серверов

        # Обновляем поле value_key (список серверов) и count_key в базе данных
        await self._update_servers_in_db()

    async def _update_servers_in_db(self):
        """Обновление списка серверов и количества серверов в базе данных"""
        value_key_json = json.dumps(self.servers)

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