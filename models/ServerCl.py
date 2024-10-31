import os
import json
from datetime import datetime

import paramiko




class Field:
    def __init__(self, name, value, server, is_protected=False):
        self._name = name  # Приватное название поля
        self._value = value  # Приватное значение поля
        self._server = server  # Ссылка на объект Server_cl
        self._is_protected = is_protected  # Флаг для защиты поля от публичного изменения

    # Публичный метод для получения значения
    async def get(self):
        return self._value

    # Приватный метод для изменения поля, если это поле защищено (is_protected=True)
    async def _set(self, new_value):
        """Приватный метод обновления значения поля."""
        self._value = new_value
        setattr(self._server, f"_{self._name}", new_value)
        await self._server.update_in_db()  # Обновление данных в базе через объект Server_cl

    # Публичный метод для изменения значения, если поле не защищено
    async def set(self, new_value):
        if self._is_protected:
            raise AttributeError(f"Field '{self._name}' is protected and cannot be changed directly.")
        await self._set(new_value)

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




class ServerCl:
    def __init__(self, server_data: dict, user):
        self.enable = Field('enable', server_data.get("enable", None), self, is_protected=True)

        # Инициализация всех полей, переданных в JSON
        self.name_protocol = Field('name_protocol', server_data.get("name_protocol", ""), self)
        self.name_server = Field('name_server', server_data.get("name_server", ""), self)
        self.name_key = Field('name_key', server_data.get("name_key", ""), self)
        self.uuid_id = Field('uuid_id', server_data.get("uuid_id", ""), self)
        self.email_key = Field('email_key', server_data.get("email_key", ""), self)
        self.country_server = Field('country_server', server_data.get("country_server", ""), self)
        self.server_ip = Field('server_ip', server_data.get("server_ip", ""), self)
        #self.user_ip = Field('user_ip', server_data.get("user_ip", ""), self)
        self.vpn_usage_start_date = Field('vpn_usage_start_date', server_data.get("vpn_usage_start_date", ""), self)
        self.traffic_up = Field('traffic_up', server_data.get("traffic_up", 0), self)
        self.traffic_down = Field('traffic_down', server_data.get("traffic_down", 0), self)
        self.has_paid_key = Field('has_paid_key', server_data.get("has_paid_key", 1), self)
        self.status_key = Field('status_key', server_data.get("status_key", 'new_user'), self)
        self.date_payment_key = Field('date_payment_key', server_data.get("date_payment_key", ""), self)
        self.date_key_off = Field('date_key_off', server_data.get("date_key_off", ""), self)
        self.date_creation_key = Field('date_creation_key', server_data.get("date_creation_key", ""), self)
        self.url_vless = Field('url_vless', server_data.get("url_vless", ""), self)
        self.user = user  # Ссылка на объект User для обновления данных в базе

    async def update_in_db(self):
        """Метод для обновления сервера в базе данных через родительский объект User."""
        await self.user._update_servers_in_db()

    async def to_dict(self):
        """Преобразуем объект сервера в JSON."""
        return {
            "name_protocol": await self.name_protocol.get(),
            "email_key": await self.email_key.get(),
            "name_key": await self.name_key.get(),
            "uuid_id": await self.uuid_id.get(),
            "name_server": await self.name_server.get(),
            "country_server": await self.country_server.get(),
            "server_ip": await self.server_ip.get(),
            "enable": await self.enable.get(),
            "vpn_usage_start_date": await self.vpn_usage_start_date.get(),
            "traffic_up": await self.traffic_up.get(),
            "traffic_down": await self.traffic_down.get(),
            "has_paid_key": await self.has_paid_key.get(),
            "status_key": await self.status_key.get(),
            "date_payment_key": await self.date_payment_key.get(),
            "date_key_off": await self.date_key_off.get(),
            "date_creation_key": await self.date_creation_key.get(),
            "url_vless": await self.url_vless.get()
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
            print(f"Сервер { await self.name_server.get()} успешно удален из списка и базы данных.")
            return True
        else:
            print("Сервер не найден в списке пользователя.")
            return False

    # async def _update_json_on_server(self, new_enable_value: bool):
    #     """Обновляет файл JSONschecна сервере через SSH и изменяет поле enable."""
    #     ssh_host = "195.133.14.202"
    #     ssh_user = "root"
    #     ssh_password = "jzH^zvfW1J4qRX"
    #     json_file_path = "/root/.wg-easy/wg0.json"
    #
    #     try:
    #         # Установка SSH-соединения
    #         print("Устанавливаем SSH-соединение...")
    #         client = paramiko.SSHClient()
    #         client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #         client.connect(ssh_host, username=ssh_user, password=ssh_password)
    #
    #         print("К серверу подключились успешно")  # Выводим фразу при успешном подключении
    #
    #         # Открываем SFTP-соединение
    #         sftp = client.open_sftp()
    #
    #         # Проверка существования файла JSON на сервере
    #         print(f"Пытаемся открыть JSON-файл по пути {json_file_path}")
    #         try:
    #             with sftp.open(json_file_path, 'r') as json_file:
    #                 wg_config = json.load(json_file)
    #             print(f"Файл {json_file_path} успешно считан с сервера.")
    #         except FileNotFoundError:
    #             print(f"Файл {json_file_path} не найден на сервере.")
    #             return
    #         except Exception as e:
    #             print(f"Ошибка при чтении файла: {e}")
    #             return
    #
    #         # Находим нужного клиента по user_ip и обновляем его enable значение
    #         client_key = next(
    #             (key for key, client in wg_config['clients'].items() if client['address'] == self.user_ip.get()), None)
    #         if client_key:
    #             print(f"Найден клиент с IP: {self.user_ip.get()}, обновляем enabled на {new_enable_value}")
    #             wg_config['clients'][client_key]['enabled'] = new_enable_value
    #             await self.enable._set(new_enable_value)  # Обновляем локально в объекте Server_cl
    #         else:
    #             print(f"Клиент с IP {self.user_ip.get()} не найден в JSON-файле.")
    #             return
    #
    #         # Записываем изменения обратно в файл на сервере
    #         print(f"Записываем изменения в файл {json_file_path}")
    #         with sftp.open(json_file_path, 'w') as json_file:
    #             json.dump(wg_config, json_file, indent=4)
    #             print(f"Файл {json_file_path} успешно обновлен на сервере")
    #
    #         # Перезапускаем WireGuard Easy через Docker
    #         print("Перезапускаем WireGuard Easy...")
    #         stdin, stdout, stderr = client.exec_command('docker restart wg-easy')
    #         stdout.channel.recv_exit_status()
    #         print("WireGuard перезапущен")
    #
    #         # Закрываем соединение
    #         sftp.close()
    #         client.close()
    #
    #     except paramiko.SSHException as ssh_err:
    #         print(f"Ошибка SSH: {ssh_err}")
    #     except Exception as e:
    #         print(f"Ошибка при обновлении JSON на сервере: {e}")
    #
    # async def change_enable(self, new_enable_value: bool):
    #     """Метод обновления enable поля на сервере и в объекте"""
    #     await self._update_json_on_server(new_enable_value)