import aiosqlite
import asyncio
import json


class Field:
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


class User:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_name = None
        self.registration_date = None
        self.referrer_id = None
        self.device = None
        self.is_subscribed_on_channel = None
        self.days_since_registration = None
        self.email = None
        self.servers = []  # Поле для хранения списка серверов (из users_key)
        self.count_key = 0  # Поле для хранения количества серверов

    async def load_user_data(self):
        async with aiosqlite.connect('/mnt/data/vpn_bot.db') as db:
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

                    self.user_name = Field('user_name', self.user_name, self)
                    self.is_subscribed_on_channel = Field('is_subscribed_on_channel', self.is_subscribed_on_channel,
                                                          self)
                    self.device = Field('device', self.device, self)
                    self.email = Field('email', self.email, self)

    async def load_servers(self):
        async with aiosqlite.connect('/mnt/data/vpn_bot.db') as db:
            query = """
            SELECT value_key, count_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    value_key, self.count_key = result  # Извлекаем значение count_key
                    try:
                        servers_data = json.loads(value_key)
                        # Добавляем сервера в список
                        self.servers = [servers_data for _ in range(self.count_key)]
                    except json.JSONDecodeError:
                        print(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                else:
                    print(f"Нет серверов для пользователя с chat_id {self.chat_id}")

    async def add_server(self, server_params):
        # Добавляем новый сервер в список servers
        self.servers.append(server_params)
        self.count_key += 1  # Увеличиваем количество серверов

        # Обновляем поле value_key в базе данных
        await self._update_servers_in_db()

    async def _update_servers_in_db(self):
        # Преобразуем список серверов обратно в JSON
        value_key_json = json.dumps(self.servers)

        async with aiosqlite.connect('/mnt/data/vpn_bot.db') as db:
            # Сначала проверяем, существует ли запись с данным chat_id
            query_check = """
            SELECT COUNT(*) FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query_check, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()
                if result[0] == 0:
                    print(f"В таблице users_key не найден chat_id: {self.chat_id}")
                    return

            # Если запись существует, обновляем value_key и count_key
            query_update = """
            UPDATE users_key 
            SET value_key = ?, count_key = ? 
            WHERE chat_id = ?
            """
            await db.execute(query_update, (value_key_json, self.count_key, self.chat_id))
            await db.commit()

    async def _update_field_in_db(self, field_name, value):
        async with aiosqlite.connect('/mnt/data/vpn_bot.db') as db:
            query = f"UPDATE users SET {field_name} = ? WHERE chat_id = ?"
            await db.execute(query, (value, self.chat_id))
            await db.commit()
