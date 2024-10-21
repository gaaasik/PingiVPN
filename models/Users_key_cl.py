from pathlib import Path
import aiosqlite
import json
from dotenv import load_dotenv
import os

# Загрузка переменных окружения из файла .env
load_dotenv()
database_path_local = Path(os.getenv('database_path_local'))

class UsersKey:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.value_key = None
        self.count_key = 0
        self.servers = []  # Поле для хранения списка серверов

    @classmethod
    async def create(cls, chat_id: int):
        self = cls(chat_id)
        await self.load_from_db()  # Загружаем данные из базы при инициализации
        return self

    async def load_from_db(self):
        """Загрузка данных из таблицы users_key для данного chat_id"""
        async with aiosqlite.connect(database_path_local) as db:
            query = """
            SELECT value_key, count_key FROM users_key WHERE chat_id = ?
            """
            async with db.execute(query, (self.chat_id,)) as cursor:
                result = await cursor.fetchone()

                if result:
                    self.value_key, self.count_key = result
                    if self.value_key:  # Если value_key не None, пытаемся загрузить JSON
                        try:
                            self.servers = json.loads(self.value_key)
                        except json.JSONDecodeError:
                            print(f"Ошибка при парсинге JSON для пользователя с chat_id {self.chat_id}")
                            self.servers = []
                    else:
                        self.servers = []
                else:
                    print(f"Нет данных для пользователя с chat_id {self.chat_id}")
                    self.servers = []

    async def save_to_db(self):
        """Сохранение текущих данных в таблицу users_key"""
        async with aiosqlite.connect(database_path_local) as db:
            value_key_json = json.dumps(self.servers)

            query = """
            UPDATE users_key 
            SET value_key = ?, count_key = ? 
            WHERE chat_id = ?
            """
            await db.execute(query, (value_key_json, self.count_key, self.chat_id))
            await db.commit()

    async def add_server(self, server_params: dict):
        """Добавление нового сервера в JSON формате и обновление count_key"""
        self.servers.append(server_params)
        self.count_key += 1  # Увеличиваем количество серверов

        # Сохраняем изменения в базе данных
        await self.save_to_db()

    async def get_server(self, index: int):
        """Возвращает сервер по индексу, если он существует"""
        if 0 <= index < len(self.servers):
            return self.servers[index]
        else:
            print(f"Сервер с индексом {index} не найден")
            return None

    async def remove_server(self, index: int):
        """Удаляет сервер по индексу"""
        if 0 <= index < len(self.servers):
            del self.servers[index]
            self.count_key -= 1  # Уменьшаем количество серверов
            await self.save_to_db()
        else:
            print(f"Сервер с индексом {index} не найден")

    async def get_status_key(self):
        """Возвращает статус ключа первого сервера или статус по умолчанию"""
        if len(self.servers) > 0:
            return self.servers[0].get('status_key', 'new_user')
        return 'new_user'
