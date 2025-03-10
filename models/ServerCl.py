import asyncio
import re
import json
from datetime import datetime
from redis_configs.redis_settings import redis_client
import redis.asyncio as redis
import logging
from typing import TYPE_CHECKING
from dotenv import load_dotenv
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.country_server_data import get_json_country_server_data, get_name_server_by_ip, get_country_server_by_ip

if TYPE_CHECKING:
    from models.UserCl import UserCl  # Только для аннотаций типов

load_dotenv()

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
    def __init__(self, name, value, server: 'ServerCl'):
        self._name = name  # Приватное название поля
        self._value = value  # Приватное значение поля
        self._server: ServerCl = server  # Ссылка на объект Server_cl

    # Публичный метод для получения значения
    async def get(self):
        return self._value

    # Приватный метод для изменения поля, если это поле защищено (is_protected=True)
    async def _set(self, new_value):
        """Приватный метод обновления значения поля."""
        self._value = new_value
        setattr(self._server, f"_{self._name}", new_value)

        if self._server in self._server.user.history_key_list:
            await self._server.update_hist_in_db()
            logging.info(f"enable Изменилось в history_key в базе данных enable={new_value}")
            return
        await self._server.update_serv_in_db()  # Обновление данных в базе через объект Server_cl

    # Публичный метод для изменения значения, если поле не защищено
    async def set(self, new_value):
        if self._name == "enable":
            await self._set_enable(new_value)
            return
        await self._set(new_value)
        # .set(False)
        # if self._is_protected:
        #     raise AttributeError(f"Field '{self._name}' is protected and cannot be changed directly.")
        # await self._set(new_value)

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

    async def get_country(self):
        # Проверка, что метод вызывается только для поля 'country_server'
        if self._name != "country_server":
            raise AttributeError("Метод get_country доступен только для поля 'country_server'.")

        #проверяем, если страна неизвестна, смотри ее в списке серверов country_server
        if self._value == "Unknown":
            country = await get_country_server_by_ip(await self._server.server_ip.get())
            await self._server.country_server.set(country)

        # Словарь переводов стран
        COUNTRY_TRANSLATIONS = {
            "USA": "🇺🇸 США",
            "Germany": "🇩🇪 Германия",
            "France": "🇫🇷 Франция",
            "Netherlands": "🇳🇱 Нидерланды",
            "Russia": "🇷🇺 Россия",
            "China": "🇨🇳 Китай",
            "Japan": "🇯🇵 Япония",
            "Poland": "🇵🇱 Польша",
            "Unknown": "🇳🇱 Нидерланды",
            "Unknown_Server": "🇳🇱 Нидерланды"
            # Добавьте другие страны, если нужно
        }

        # Получаем страну из поля и возвращаем перевод
        country = self._value
        return COUNTRY_TRANSLATIONS.get(country, "Неизвестная страна")

    # Использование данных в функциях
    async def _set_enable(self, enable_value: bool):
        """Обновляет значение enable и отправляет задачу в Redis."""

        country_server_data = await get_json_country_server_data()

        if self._name != "enable":
            raise AttributeError("Метод set_enable можно вызывать только для поля 'enable'.")

        if country_server_data is None:
            raise RuntimeError("Данные серверов не загружены. Проверьте вызов load_server_data().")

        # Получаем данные объекта
        chat_id = self._server.user.chat_id
        name_protocol = await self._server.name_protocol.get()
        uuid_value = await self._server.uuid_id.get()
        server_ip = await self._server.server_ip.get()
        user_ip = await self._server.user_ip.get()

        # Получаем имя сервера
        server_name = self.__get_server_name_by_ip(country_server_data, server_ip)

        # Формируем задачу
        task_data = {
            "task_type": "change_enable_user",
            "name_protocol": name_protocol,
            "chat_id": chat_id,
            "server_ip": server_ip,
            "user_ip": user_ip,
            "uuid_value": uuid_value,
            "enable": enable_value,
        }
        queue_name = f"queue_task_{server_name}"
        logging.info(f"Формируется очередь: {queue_name}")

        # Используем redis.asyncio вместо aioredis

        try:
            await redis_client.rpush(queue_name, json.dumps(task_data))
            logging.info(f"Задача добавлена в очередь {queue_name}: {task_data}")
            if queue_name == "queue_task_Unknown_Server":
                await send_admin_log(bot,
                                     f"❌Пользователь {chat_id} не изменил состояние на {enable_value}, задача в очереди queue_task_Unknown_Server")
        except Exception as e:
            logging.error(f"Ошибка при добавлении задачи в очередь {queue_name}: {e}")
        finally:
            try:
                pass

            except Exception as e:
                logging.error(f"Ошибка с redis_client")

    async def set_enable_admin(self, enable_value: bool):
        """Напрямую обновление в базе данных значения поля enable"""

        if self._name != "enable":
            raise AttributeError("Метод set_enable_admin можно вызывать только для поля 'enable'.")

        # Обновляем значение в объекте и в базе данных
        await self._set(enable_value)
        logging.info(f"enable Изменилось в value_key в базе данных enable={enable_value}")

    def __get_server_name_by_ip(self, server_data, ip_address: str) -> str:
        """Получает имя сервера по его IP."""
        for server in server_data.get("servers", []):
            if server.get("address") == ip_address:
                return server.get("name", "Unknown_Server")
        return "Unknown_Server"


class ServerCl:
    def __init__(self, server_data: dict, user: "UserCl"):
        # Инициализация всех полей, переданных в JSON
        self.country_server = Field('country_server', server_data.get("country_server", ""), self)
        self.date_creation_key = Field('date_creation_key', server_data.get("date_creation_key", ""), self)
        self.date_key_off = Field('date_key_off', server_data.get("date_key_off", ""), self)
        self.date_latest_handshake = Field('date_latest_handshake', server_data.get("date_latest_handshake", ""), self)
        self.date_payment_key = Field('date_payment_key', server_data.get("date_payment_key", ""), self)
        self.email_key = Field('email_key', server_data.get("email_key", ""), self)
        self.enable = Field('enable', server_data.get("enable", None), self)
        self.has_paid_key = Field('has_paid_key', server_data.get("has_paid_key", 1), self)
        self.name_key = Field('name_key', server_data.get("name_key", ""), self)
        self.name_protocol = Field('name_protocol', server_data.get("name_protocol", ""), self)
        self.name_server = Field('name_server', server_data.get("name_server", ""), self)
        self.server_ip = Field('server_ip', server_data.get("server_ip", ""), self)
        self.status_key = Field('status_key', server_data.get("status_key", 'new_user'), self)
        self.traffic_down = Field('traffic_down', server_data.get("traffic_down", 0), self)
        self.traffic_up = Field('traffic_up', server_data.get("traffic_up", 0), self)
        self.url_vless = Field('url_vless', server_data.get("url_vless", ""), self)
        self.user_ip = Field('user_ip', server_data.get("user_ip", ""), self)
        self.uuid_id = Field('uuid_id', server_data.get("uuid_id", ""), self)
        self.user = user  # Ссылка на объект User для обновления данных в базе

    async def update_serv_in_db(self):
        """Метод для обновления сервера в базе данных через родительский объект User."""
        await self.user._update_servers_in_db()

    async def update_hist_in_db(self):
        """Метод для обновления сервера в базе данных через родительский объект User."""
        await self.user._update_history_key_in_db()

    async def to_dict(self):
        """Преобразуем объект сервера в JSON."""
        return {

            "country_server": await self.country_server.get(),
            "date_creation_key": await self.date_creation_key.get(),
            "date_latest_handshake": await self.date_latest_handshake.get(),
            "date_key_off": await self.date_key_off.get(),
            "date_payment_key": await self.date_payment_key.get(),
            "email_key": await self.email_key.get(),
            "enable": await self.enable.get(),
            "has_paid_key": await self.has_paid_key.get(),
            "name_key": await self.name_key.get(),
            "name_protocol": await self.name_protocol.get(),
            "name_server": await self.name_server.get(),
            "server_ip": await self.server_ip.get(),
            "status_key": await self.status_key.get(),
            "traffic_down": await self.traffic_down.get(),
            "traffic_up": await self.traffic_up.get(),
            "url_vless": await self.url_vless.get(),
            "user_ip": await self.user_ip.get(),
            "uuid_id": await self.uuid_id.get()
        }

    async def delete(self):
        """Удаляет текущий сервер из списка серверов пользователя и обновляет базу данных."""

        # Проверяем, что текущий сервер есть в списке servers пользователя
        if self in self.user.servers:
            # Удаляем сервер из списка servers
            self.user.servers.remove(self)

            # Обновляем value_key в базе данных (список серверов) после удаления
            await self.user._update_servers_in_db()
            # Обновляем count_key
            await self.user.count_key._update_count_key()
            print(f"Ключ {await self.name_server.get()} успешно удален из списка и базы данных.")
            return True
        else:
            print("Сервер не найден в списке пользователя.")
            return False

    async def delete_user_key(self):
        """
        Отправляет задачу на удаление пользователя на сервере в очередь Redis.
        """
        chat_id = self.user.chat_id
        try:

            # Получаем данные объекта
            uuid_id = await self.uuid_id.get()
            server_ip = await self.server_ip.get()
            name_protocol = await self.name_protocol.get()
            email_key = await self.email_key.get()
            server_name = await get_name_server_by_ip(server_ip)
            user_ip = await self.user_ip.get()

            task_data = {}

            if name_protocol == "vless":
                # Формируем данные задачи
                task_data = {
                    "task_type": "delete_user",
                    "chat_id": chat_id,
                    "uuid_id": uuid_id,
                    "server_ip": server_ip,
                    "name_protocol": name_protocol,
                    "email_key": email_key
                }
            elif name_protocol == "wireguard":
                # Формируем данные задачи
                task_data = {
                    "task_type": "delete_user",
                    "chat_id": chat_id,
                    "server_ip": server_ip,
                    "name_protocol": name_protocol,
                    "user_ip": user_ip
                }

            # Формируем имя очереди
            queue_name = f"queue_task_{server_name}"
            logging.info(f"Формируется очередь для удаления ключа: {queue_name}")

            # Отправка задачи в Redis
            await redis_client.rpush(queue_name, json.dumps(task_data))
            logging.info(f"Задача удаления ключа добавлена в очередь {queue_name}: {task_data}")

            # Уведомление администратора
            await send_admin_log(
                bot, f"🗝 Задача на удаление ключа пользователя {chat_id} добавлена в очередь {queue_name}."
            )

        except Exception as e:
            logging.error(f"Ошибка при отправке задачи на удаление ключа: {e}")
            await send_admin_log(
                bot, f"❌ Ошибка при отправке задачи на удаление ключа пользователя {chat_id}: {e}"
            )
        finally:
            try:
                if redis_client:
                    await redis_client.close()
            except Exception as e:
                logging.error(f"Ошибка при закрытии соединения с Redis: {e}")






