import os
import json
import paramiko


class Server_cl:
    def __init__(self, server_data: dict, user):
        self.enable = Field('enable', server_data.get("enable", None), self, is_protected=True)

        # Инициализация всех полей, переданных в JSON
        self.name_server = Field('name_server', server_data.get("name_server", None), self)
        self.country_server = Field('country_server', server_data.get("country_server", None), self)
        self.server_ip = Field('server_ip', server_data.get("server_ip", None), self)
        self.user_ip = Field('user_ip', server_data.get("user_ip", None), self)
        self.name_conf = Field('name_conf', server_data.get("name_conf", None), self)
        self.vpn_usage_start_date = Field('vpn_usage_start_date', server_data.get("vpn_usage_start_date", None), self)
        self.traffic_up = Field('traffic_up', server_data.get("traffic_up", 0), self)
        self.traffic_down = Field('traffic_down', server_data.get("traffic_down", 0), self)
        self.has_paid_key = Field('has_paid_key', server_data.get("has_paid_key", 1), self)
        self.status_key = Field('status_key', server_data.get("status_key", 'new_user'), self)
        self.is_notification = Field('is_notification', server_data.get("is_notification", False), self)
        self.days_after_pay = Field('days_after_pay', server_data.get("days_after_pay", None), self)
        self.date_payment_key = Field('date_payment_key', server_data.get("date_payment_key", None), self)
        self.date_expire_of_paid_key = Field('date_expire_of_paid_key', server_data.get("date_expire_of_paid_key", None), self)
        self.date_expire_free_trial = Field('date_expire_free_trial', server_data.get("date_expire_free_trial", None), self)
        self.user = user  # Ссылка на объект User для обновления данных в базе

    async def update_in_db(self):
        """Метод для обновления сервера в базе данных через родительский объект User."""
        await self.user._update_servers_in_db()

    def to_dict(self):
        """Преобразуем объект сервера в JSON."""
        return {
            "name_server": self.name_server.get(),
            "country_server": self.country_server.get(),
            "server_ip": self.server_ip.get(),
            "user_ip": self.user_ip.get(),
            "name_conf": self.name_conf.get(),
            "enable": self.enable.get(),
            "vpn_usage_start_date": self.vpn_usage_start_date.get(),
            "traffic_up": self.traffic_up.get(),
            "traffic_down": self.traffic_down.get(),
            "has_paid_key": self.has_paid_key.get(),
            "status_key": self.status_key.get(),
            "is_notification": self.is_notification.get(),
            "days_after_pay": self.days_after_pay.get(),
            "date_payment_key": self.date_payment_key.get(),
            "date_expire_of_paid_key": self.date_expire_of_paid_key.get(),
            "date_expire_free_trial": self.date_expire_free_trial.get()
        }

    async def _update_json_on_server(self, new_enable_value: bool):
        """Обновляет файл JSON на сервере через SSH и изменяет поле enable."""
        ssh_host = "195.133.14.202"
        ssh_user = "root"
        ssh_password = "jzH^zvfW1J4qRX"
        json_file_path = "/root/.wg-easy/wg0.json"

        try:
            # Установка SSH-соединения
            print("Устанавливаем SSH-соединение...")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ssh_host, username=ssh_user, password=ssh_password)

            print("К серверу подключились успешно")  # Выводим фразу при успешном подключении

            # Открываем SFTP-соединение
            sftp = client.open_sftp()

            # Проверка существования файла JSON на сервере
            print(f"Пытаемся открыть JSON-файл по пути {json_file_path}")
            try:
                with sftp.open(json_file_path, 'r') as json_file:
                    wg_config = json.load(json_file)
                print(f"Файл {json_file_path} успешно считан с сервера.")
            except FileNotFoundError:
                print(f"Файл {json_file_path} не найден на сервере.")
                return
            except Exception as e:
                print(f"Ошибка при чтении файла: {e}")
                return

            # Находим нужного клиента по user_ip и обновляем его enable значение
            client_key = next(
                (key for key, client in wg_config['clients'].items() if client['address'] == self.user_ip.get()), None)
            if client_key:
                print(f"Найден клиент с IP: {self.user_ip.get()}, обновляем enabled на {new_enable_value}")
                wg_config['clients'][client_key]['enabled'] = new_enable_value
                await self.enable._set(new_enable_value)  # Обновляем локально в объекте Server_cl
            else:
                print(f"Клиент с IP {self.user_ip.get()} не найден в JSON-файле.")
                return

            # Записываем изменения обратно в файл на сервере
            print(f"Записываем изменения в файл {json_file_path}")
            with sftp.open(json_file_path, 'w') as json_file:
                json.dump(wg_config, json_file, indent=4)
                print(f"Файл {json_file_path} успешно обновлен на сервере")

            # Перезапускаем WireGuard Easy через Docker
            print("Перезапускаем WireGuard Easy...")
            stdin, stdout, stderr = client.exec_command('docker restart wg-easy')
            stdout.channel.recv_exit_status()
            print("WireGuard перезапущен")

            # Закрываем соединение
            sftp.close()
            client.close()

        except paramiko.SSHException as ssh_err:
            print(f"Ошибка SSH: {ssh_err}")
        except Exception as e:
            print(f"Ошибка при обновлении JSON на сервере: {e}")

    async def change_enable(self, new_enable_value: bool):
        """Метод обновления enable поля на сервере и в объекте"""
        await self._update_json_on_server(new_enable_value)


class Field:
    def __init__(self, name, value, server, is_protected=False):
        self._name = name  # Приватное название поля
        self._value = value  # Приватное значение поля
        self._server = server  # Ссылка на объект Server_cl
        self._is_protected = is_protected  # Флаг для защиты поля от публичного изменения

    # Публичный метод для получения значения
    def get(self):
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
