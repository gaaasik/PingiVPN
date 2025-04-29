import asyncio
import base64
import json
import secrets
import string
import subprocess
import uuid
from datetime import time
import random
from typing import Dict, Optional
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import aiohttp
import aiosqlite

from logging_config.my_logging import my_logging
from task_processor.server_settings import ServerSettings
from task_processor.protocols.base_class import VPNProcessor


#from main import ServerSettings


class VlessProcessor(VPNProcessor):
    """Обработчик задач для VLESS."""

    async def process_change_enable_user(self, task_data: Dict):
        my_logging.info(f"VLESS: Обработка задачи {task_data}")
        uuid_value = task_data["uuid_value"]
        enable = task_data["enable"]
        chat_id = task_data["chat_id"]
        enable_now = await self.get_user_enable_status(uuid_value)
        # Подключаемся к базе данных
        db = await aiosqlite.connect(ServerSettings.PATH_DATABASE_X_UI)

        try:
            # Ищем пользователя по UUID
            async with db.execute("SELECT id, settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                user_found = None
                async for inbound in cursor:
                    inbound_id, settings = inbound
                    settings_json = json.loads(settings)
                    for client in settings_json.get("clients", []):
                        if client.get("id") == uuid_value:
                            user_found = (inbound_id, settings_json, client)
                            break

            if not user_found:
                my_logging.warning(f"VLESS: Пользователь с UUID {uuid_value} не найден.")
                return

            # Обновляем параметр "enable"
            inbound_id, settings_json, client = user_found
            client["enable"] = enable
            updated_settings = json.dumps(settings_json)

            # Записываем обратно в базу данных
            await db.execute("UPDATE inbounds SET settings = ? WHERE id = ?", (updated_settings, inbound_id))
            await db.commit()
            my_logging.info(
                f"VLESS: Изменено состояние пользователя {uuid_value}: {'Включен' if enable else 'Выключен'}")

            # Получаем актуальный трафик и статус
            traffic_info = await self.get_user_traffic(uuid_value)
            enable_status = await self.get_user_enable_status(uuid_value)

            # Формируем результат
            result = {
                "status": "success",
                "task_type": "result_change_enable_user",
                "chat_id": chat_id,
                "protocol": "vless",
                "enable": enable_status,
                "traffic": traffic_info,
                "uuid_value": uuid_value,
                "action": "enabled" if enable_status else "disabled"
            }

            # Отправляем в очередь результатов
            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.info(
                f"VLESS: Задача обработана и отправлена в очередь {ServerSettings.NAME_RESULT_QUEUE}: {result}")

            if enable != enable_now:
                await VlessProcessor.restart_x_ui()

        except Exception as e:
            error_msg = f"VLESS: Ошибка при изменении состояния пользователя {uuid_value}: {e}"
            my_logging.error(error_msg)
            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE,
                                     json.dumps({"status": "error", "message": error_msg}))
        finally:
            await db.close()

    async def get_user_traffic(self, uuid_value: str) -> Dict:
        return {"transfer_received": "0", "transfer_sent": "0"}  # Заглушка

    async def get_user_enable_status(self, uuid_value: str) -> bool:
        try:
            async with aiosqlite.connect(ServerSettings.PATH_DATABASE_X_UI) as db:
                async with db.execute("SELECT settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                    async for inbound in cursor:
                        settings_json = json.loads(inbound[0])
                        for client in settings_json.get("clients", []):
                            if client.get("id") == uuid_value:
                                return client.get("enable", False)
        except Exception as e:
            my_logging.error(f"Ошибка получения состояния пользователя VLESS: {e}")
        return False

    async def get_count_true_user(self) -> int:
        """
        📊 Возвращает количество VLESS-пользователей с enabled=True.
        """
        try:
            count = 0
            async with aiosqlite.connect(ServerSettings.PATH_DATABASE_X_UI) as db:
                async with db.execute("SELECT settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                    async for row in cursor:
                        try:
                            settings_json = json.loads(row[0])
                            clients = settings_json.get("clients", [])
                            count += sum(1 for c in clients if c.get("enable") is True)
                        except Exception as parse_err:
                            my_logging.error(f"Ошибка парсинга settings JSON: {parse_err}")
                            continue

            my_logging.info(f"Найдено включённых VLESS-пользователей: {count}")
            return count
        except Exception as e:
            my_logging.error(f"Ошибка при подсчёте активных VLESS-пользователей: {e}")
            return 0

    async def process_delete_user(self, task_data: Dict):
        """Полное удаление пользователя VLESS из базы данных x-ui и связанных таблиц."""
        db_path = ServerSettings.PATH_DATABASE_X_UI
        uuid_id = task_data["uuid_id"]
        email_key = task_data["email_key"]
        chat_id = task_data["chat_id"]

        try:
            async with aiosqlite.connect(db_path) as db:
                my_logging.info(f"Начато удаление пользователя: UUID={uuid_id}, Email={email_key}")

                # 1️⃣ Обновляем таблицу inbounds (удаляем пользователя из settings)
                user_found = False
                async with db.execute("SELECT id, settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                    async for inbound in cursor:
                        inbound_id, settings = inbound
                        try:
                            settings_json = json.loads(settings)
                        except json.JSONDecodeError as json_err:
                            my_logging.error(f"Ошибка при парсинге settings JSON: {json_err}")
                            continue

                        original_clients = settings_json.get("clients", [])
                        updated_clients = [c for c in original_clients if c.get("id") != uuid_id]

                        if len(original_clients) != len(updated_clients):
                            settings_json["clients"] = updated_clients
                            updated_settings = json.dumps(settings_json)

                            await db.execute(
                                "UPDATE inbounds SET settings = ? WHERE id = ?",
                                (updated_settings, inbound_id)
                            )
                            user_found = True

                # 2️⃣ Удаляем данные пользователя из client_traffics
                result_traffic = await db.execute(
                    "DELETE FROM client_traffics WHERE email = ?",
                    (email_key,)
                )

                # 3️⃣ Удаляем пользователя из users
                result_user = await db.execute(
                    "DELETE FROM users WHERE username = ?",
                    (email_key,)
                )

                # 4️⃣ Подтверждение удаления
                try:
                    await db.commit()
                except Exception as commit_error:
                    my_logging.error(f"Ошибка при фиксации транзакции: {commit_error}")

                # 5️⃣ Подтверждение удаления в Redis
                redis_client = await ServerSettings.get_redis_client()
                result_status = "success" if user_found else "not_found"

                result = {
                    "status": result_status,
                    "task_type": "result_delete_user",
                    "chat_id": chat_id,
                    "protocol": "vless",
                    "uuid_id": uuid_id,
                    "action": "deleted" if user_found else "user_not_found"
                }

                await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
                my_logging.info(f"Удаление пользователя завершено. Результат: {result}")
        except Exception as e:
            error_msg = f"Ошибка при удалении пользователя {uuid_id}: {e}"
            my_logging.error(error_msg)
            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps({
                "status": "error",
                "message": error_msg
            }))

    @staticmethod
    async def restart_x_ui():
        """
        Перезапуск 3x-ui с использованием команды systemctl.
        """
        try:
            subprocess.run(["sudo", "systemctl", "restart", "x-ui"], check=True)
            my_logging.info(" Сервис 3x-ui успешно перезапущен через systemctl.")
        except subprocess.CalledProcessError as e:
            my_logging.error(f" Ошибка при перезапуске 3x-ui через systemctl: {e}")

        # 🔄 Альтернативный метод: вызов API x-ui для применения изменений в реальном времени

    @staticmethod
    async def generate_vless_username(db) -> Optional[str]:
        """
        🔄 Генерирует уникальное имя пользователя VLESS в формате:
        PingiVPN_<число>_<страна>, начиная с server_number, если пользователи отсутствуют или формат нарушен.

        :param server_ip: IP-адрес сервера.
        :param db: Асинхронное подключение к базе данных.
        :return: Гарантированно уникальное имя пользователя.
        """
        try:
            # 📡 Загружаем данные о сервере
            server_ip = ServerSettings.SERVER_IP
            server_name = ServerSettings.SERVER_NAME
            country = ServerSettings.SERVER_COUNTRY

            my_logging.info(f"server_info: {server_ip}, {server_name}, {country}")

            if not country:
                my_logging.error(f"Страна не найдена в server_info.")
                return None

            my_logging.info(f"Страна сервера: {country}")
            my_logging.info(f"Название сервера: {server_name}")

            # 📏 Извлечение числа из имени сервера
            parts = server_name.split("_")
            numbers = [word for word in parts if word.isdigit()]
            server_number = sum(int(word) for word in numbers) if numbers else 99000  # Значение по умолчанию

            my_logging.info(f"Итоговое число сервера: {server_number}")

            # 🏃‍♂️ Сбор существующих номеров пользователей из inbounds.settings
            existing_numbers = set()
            async with db.execute("SELECT settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                async for row in cursor:
                    settings_json = json.loads(row[0])
                    clients = settings_json.get("clients", [])
                    for client in clients:
                        email = client.get("email", "")
                        if email.startswith("PingiVPN_") and email.endswith(f"_{country}"):
                            try:
                                num_part = int(email.split("_")[1])
                                existing_numbers.add(num_part)
                            except (ValueError, IndexError):
                                continue

            # 📌 Добавляем проверку уникальности имени в client_traffics
            async def email_exists(email_key: str) -> bool:
                async with db.execute("SELECT 1 FROM client_traffics WHERE email = ?", (email_key,)) as cursor:
                    return await cursor.fetchone() is not None

            # 🔄 Поиск минимально доступного номера
            for num in range(server_number, server_number + 100):  # Проверяем ближайшие 100 номеров
                if num not in existing_numbers:
                    email_key = f"PingiVPN_{num}_{country}"
                    if not await email_exists(email_key):  # Проверяем уникальность в client_traffics
                        my_logging.info(f"Сгенерировано имя пользователя: {email_key}")
                        return email_key

            # 🏗 Если все номера заняты — берем следующий доступный номер
            next_number = max(existing_numbers, default=server_number - 1) + 1
            email_key = f"PingiVPN_{next_number}_{country}"
            if await email_exists(email_key):
                my_logging.error(f"❌ Ошибка: даже next_number {next_number} уже существует!")
                return None

            my_logging.info(f"✅ Все номера заняты. Сгенерировано имя: {email_key}")
            return email_key

        except Exception as e:
            my_logging.error(f"❌ Ошибка при генерации имени пользователя: {e}")
            return None

    @staticmethod
    def generate_vless_url(server_ip, uuid_id, public_key, sni, sid, email_key, port=443):
        """
        🌐 Генерация VLESS URL для подключения пользователя с полными параметрами.
        """
        return (
            f"vless://{uuid_id}@{server_ip}:{port}?type=tcp&security=reality&"
            f"pbk={public_key}&fp=chrome&sni={sni}&sid={sid}&spx=%2F&flow=xtls-rprx-vision#{email_key}"
        )

    @staticmethod
    def sort_clients_by_name_and_number(clients):
        """
        🏃‍♂️ Сортировка клиентов:
        - Сначала пользователи с обычными именами (не начинающимися с PingiVPN_)
        - Затем пользователи PingiVPN_ по порядку номера
        """
        def sort_key(client):
            email = client.get("email", "")
            if email.startswith("PingiVPN_"):
                try:
                    return (1, int(email.split("_")[1]))  # Сортировка по числу для PingiVPN_
                except (IndexError, ValueError):
                    return 1, float("inf")
            return 0, email  # Обычные имена в начале

        return sorted(clients, key=sort_key)

    async def creating_user(self, task_data: Dict, count_users=3):
        """
        🏗 Создание пользователя VLESS с правильным порядком, генерацией subId и сортировкой клиентов.
        """
        db_path = ServerSettings.PATH_DATABASE_X_UI
        server_ip = ServerSettings.SERVER_IP
        server_name = ServerSettings.SERVER_NAME
        flow = "xtls-rprx-vision"

        created_users = []
        all_urls = []

        try:
            async with aiosqlite.connect(db_path) as db:
                my_logging.info(f"🚀 Начато создание {count_users} пользователей для сервера: {server_ip}")

                # 1️⃣ Обновляем таблицу inbounds (добавление пользователей в clients)
                async with db.execute("SELECT id, stream_settings FROM inbounds WHERE protocol = 'vless'") as cursor:
                    async for row in cursor:
                        try:
                            inbound_id, stream_settings_json = row
                            stream_settings_json = json.loads(stream_settings_json)  # Декодируем JSON
                            reality_settings = stream_settings_json.get("realitySettings", {})

                            public_key = reality_settings.get("settings", {}).get("publicKey", "")
                            sni = reality_settings.get("serverNames", [""])[0]  # Берем первый сервер
                            sid = reality_settings.get("shortIds", [""])[0]  # Берем первый shortId
                            fingerprint = reality_settings.get("settings", {}).get("fingerprint", "chrome")
                            spx = reality_settings.get("settings", {}).get("spiderX", "/")
                        except json.JSONDecodeError as json_err:
                            my_logging.error(f"❌ Ошибка при парсинге JSON: {json_err}")
                            continue

                        # Получаем настройки пользователей
                        async with db.execute("SELECT id, settings FROM inbounds WHERE id = ?",
                                              (inbound_id,)) as settings_cursor:
                            async for settings_row in settings_cursor:
                                _, settings_json = settings_row
                                settings_json = json.loads(settings_json)
                                settings_json.setdefault("clients", [])  # ✅ Убеждаемся, что есть clients

                        # ⚡ Создание пользователей
                        for _ in range(count_users):
                            uuid_id = str(uuid4())  # 🛡 Генерация UUID пользователя

                            # 📌 Исправленный вызов generate_vless_username() с передачей db и server_ip
                            email_key = await self.generate_vless_username(db)
                            subId = str(uuid4()).replace("-", "")[0:16]
                            url_vless = self.generate_vless_url(server_ip, uuid_id, public_key, sni, sid, email_key)
                            if not email_key or not url_vless or not subId or not flow or not url_vless or not server_ip:
                                my_logging.error(f"Не сгенерирован обязательный параметр")
                                continue
                            # ⚡ Создаем json одного пользователя
                            new_client = {
                                "email": email_key,
                                "enable": True,
                                "expiryTime": 0,
                                "flow": flow,
                                "id": uuid_id,
                                "limitIp": 0,
                                "reset": 0,
                                "subId": subId,
                                "tgId": "",
                                "totalGB": 0
                            }
                            settings_json["clients"].append(new_client)

                            # 📦 Сохраняем данные для ответа
                            created_users.append({
                                "uuid_id": uuid_id,
                                "email_key": email_key,
                                "subId": subId,
                                "url": url_vless
                            })
                            all_urls.append(url_vless)

                            # 2️⃣ Добавление данных в client_traffics
                            await db.execute(
                                "INSERT INTO client_traffics (inbound_id, enable, email, up, down, expiry_time, total, reset)"
                                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (inbound_id, 1, email_key, 0, 0, 0, 0, 0)
                            )

                        # 🏃‍♂️ Сортируем клиентов:
                        settings_json["clients"] = self.sort_clients_by_name_and_number(settings_json["clients"])

                        updated_settings = json.dumps(settings_json)
                        await db.execute(
                            "UPDATE inbounds SET settings = ? WHERE id = ?",
                            (updated_settings, inbound_id)
                        )
                        my_logging.info(f"✅ {count_users} пользователей успешно добавлены и отсортированы в inbounds.")

                # 3️⃣ Подтверждение всех изменений
                await db.commit()
                #await VlessProcessor.add_client_traffic(inbound_id, email_key)
                my_logging.info("🎯 Транзакция успешно зафиксирована.")

                # 4️⃣ Отправка подтверждения в Redis
                redis_client = await ServerSettings.get_redis_client()
                result = {
                    "status": "success",
                    "server_id": server_ip,
                    "server_name": server_name,
                    "task_type": "result_create_user",
                    "protocol": "vless",
                    "count_users": len(created_users),
                    "all_urls": all_urls,
                    "action": "created_batch"
                }
                await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
                await asyncio.sleep(2)  # ⏱️ Даём Redis и очереди отработать
                await self.restart_x_ui()  # 🔄 Перезапуск 3x-ui
                my_logging.info(f"Создание {count_users} пользователей завершено. Результат: {result}")

        except Exception as e:
            error_msg = f"Ошибка при создании пользователя {e}"
            my_logging.error(error_msg)
            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps({
                "status": "error",
                "server_id": server_ip,
                "server_name": server_name,
                "task_type": "result_create_user",
                "error_msg": error_msg
            }))

    @staticmethod
    async def add_client_traffic(inbound_id, email_key):
        try:
            my_logging.info("🌀 Вход в add_client_traffic")
            db_path = ServerSettings.PATH_DATABASE_X_UI

            async with aiosqlite.connect(db_path) as db:
                my_logging.info("Проверка существующей записи в client_traffics")

                # 1️⃣ Удалить существующую запись с таким же email
                await db.execute(
                    "DELETE FROM client_traffics WHERE email = ?",
                    (email_key,)
                )
                my_logging.info(f"Удалена старая запись с email = {email_key} (если была)")

                # 2️⃣ Вставка новой записи
                await db.execute(
                    """
                    INSERT INTO client_traffics (
                        inbound_id, enable, email, up, down, expiry_time, total, reset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (inbound_id, 1, email_key, 0, 0, 0, 0, 0)
                )
                await db.commit()
                my_logging.info(f"Добавлена новая запись для email = {email_key}")

        except Exception as e:
            my_logging.error(f"Ошибка в add_client_traffic: {e}")

    @staticmethod
    def generate_reality_keys():
        private_key_obj = x25519.X25519PrivateKey.generate()
        public_key_obj = private_key_obj.public_key()

        # Сериализуем в "сыром" виде (raw) и кодируем в base64url без паддинга
        private_key = base64.urlsafe_b64encode(
            private_key_obj.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
        ).decode().rstrip("=")

        public_key = base64.urlsafe_b64encode(
            public_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode().rstrip("=")

        return private_key, public_key

    @staticmethod
    def generate_short_ids() -> list[str]:
        """
        Генерирует 8 shortIds фиксированных и случайных длин, как в рабочем примере.
        """
        lengths = [4, 6, 8, 10, 12, 14, 16]
        short_ids = []

        for _ in range(8):
            length = random.choice(lengths)
            # Генерация hex-строки нужной длины (в байтах)
            short_id = secrets.token_hex(length // 2)
            short_ids.append(short_id)

        return short_ids

    @staticmethod
    async def create_xui_inbound_from_task():
        user_uuid = str(uuid.uuid4())
        user_subid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        short_ids = VlessProcessor.generate_short_ids()
        private_key, public_key = VlessProcessor.generate_reality_keys()

        inbound_data = {
            "remark": "",
            "tag": "inbound-443",
            "settings": {
                "clients": [{
                    "comment": "",
                    "email": "test",
                    "enable": True,
                    "expiryTime": 0,
                    "flow": "xtls-rprx-vision",
                    "id": user_uuid,
                    "limitIp": 0,
                    "reset": 0,
                    "subId": user_subid,
                    "tgId": "",
                    "totalGB": 0,
                }],
                "decryption": "none",
                "fallbacks": []
            },
            "stream_settings": {
                "externalProxy": [],
                "network": "tcp",
                "realitySettings": {
                    "dest": "google.com:443",
                    "maxClient": "",
                    "maxTimediff": 0,
                    "minClient": "",
                    "privateKey": private_key,
                    "serverNames": [
                        "google.com",
                        "www.google.com"
                    ],
                    "settings": {
                        "fingerprint": "chrome",
                        "publicKey": public_key,
                        "serverName": "",
                        "spiderX": "/"
                    },
                    "shortIds": short_ids,
                    "show": False,
                    "xver": 0
                },
                "security": "reality",
                "tcpSettings": {
                    "acceptProxyProtocol": False,
                    "header": {
                        "type": "none"
                    }
                }
            },

            "sniffing": {
                "enabled": False,
                "metadataOnly": False,
                "routeOnly": False,
                "destOverride": ["http", "tls", "quic", "fakedns"]
            },
            "allocate": {
                "strategy": "always",
                "refresh": 5,
                "concurrency": 3
            }
        }

        await VlessProcessor.write_to_x_ui_database(inbound_data)

    @staticmethod
    async def write_to_x_ui_database(inbound_data: dict):
        db_path = ServerSettings.PATH_DATABASE_X_UI
        email = inbound_data["settings"]["clients"][0]["email"]
        query = """
        INSERT INTO inbounds (
            user_id, up, down, total, remark, enable, expiry_time, listen, port, protocol,
            settings, stream_settings, tag, sniffing, allocate
        ) VALUES (
            1, 0, 0, 0, ?, 1, 0, '', 443, 'vless',
            ?, ?, ?, ?, ?
        );
        """
        async with aiosqlite.connect(db_path) as db:
            await db.execute(query, (
                inbound_data["remark"],
                json.dumps(inbound_data["settings"], separators=(',', ':')),
                json.dumps(inbound_data["stream_settings"], separators=(',', ':')),
                inbound_data["tag"],
                json.dumps(inbound_data["sniffing"], separators=(',', ':')),
                json.dumps(inbound_data["allocate"], separators=(',', ':'))
            ))
            await db.commit()  # ✅ теперь всё корректно

        # После commit – добавляем запись в client_traffics
        await VlessProcessor.add_client_traffic(1, email)