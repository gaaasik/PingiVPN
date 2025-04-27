import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4

import aiofiles
from task_processor.server_settings import ServerSettings
from logging_config.my_logging import my_logging
from task_processor.protocols.base_class import VPNProcessor


class WireGuardProcessor(VPNProcessor):
    """Обработчик задач для WireGuard."""

    async def process_change_enable_user(self, task_data: Dict):
        my_logging.info(f"WireGuard: Обработка задачи {task_data}")
        user_ip = task_data["user_ip"]
        enable = task_data["enable"]
        chat_id = task_data["chat_id"]

        try:
            async with aiofiles.open(ServerSettings.PATH_PRIMARY_WG_JSON, mode="r", encoding="utf-8") as file:
                wg_config = json.loads(await file.read())

            user_found = False
            for client in wg_config["clients"].values():
                if client["address"] == user_ip:
                    user_found = True
                    public_key = client["publicKey"]
                    pre_shared_key = client.get("preSharedKey", "")
                    client["enabled"] = enable

                    async with aiofiles.open(ServerSettings.PATH_PRIMARY_WG_JSON, mode="w", encoding="utf-8") as file:
                        await file.write(json.dumps(wg_config, indent=4))

                    command = (
                        f'echo "{pre_shared_key}" | docker exec -i wg-easy '
                        f"sh -c 'wg set wg0 peer {public_key} allowed-ips {user_ip}/32 preshared-key /dev/stdin'"
                    ) if enable else [
                        "docker", "exec", "-i", "wg-easy",
                        "wg", "set", "wg0", "peer", public_key, "remove"
                    ]

                    await self.run_command(command)
                    break

            if not user_found:
                my_logging.warning(f"WireGuard: Пользователь с IP {user_ip} не найден.")
                return

            # Получаем актуальные данные
            traffic_info = await self.get_user_traffic(user_ip)
            enable_status = await self.get_user_enable_status(user_ip)

            result = {
                "status": "success",
                "task_type": "result_change_enable_user",
                "chat_id": chat_id,
                "protocol": "wireguard",
                "enable": enable_status,
                "traffic": traffic_info,
                "user_ip": user_ip,
                "action": "enabled" if enable_status else "disabled"
            }

            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.info(f"WireGuard: Задача обработана и отправлена в очередь {ServerSettings.NAME_RESULT_QUEUE}: {result}")

        except Exception as e:
            my_logging.error(f"WireGuard: Ошибка обработки задачи: {e}")

    async def run_command(self, command):
        """Выполняет команду в системе и логирует ошибки в Redis."""
        try:
            process = await asyncio.create_subprocess_shell(
                command if isinstance(command, str) else " ".join(command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = f"Команда завершилась с ошибкой: {stderr.decode().strip()}"
                my_logging.error(error_msg)
                redis_client = await ServerSettings.get_redis_client()
                await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE,
                                         json.dumps({"status": "error", "message": error_msg}))
                return

            my_logging.info(f"Команда успешно выполнена: {stdout.decode().strip()}")

        except Exception as e:
            error_msg = f"Ошибка выполнения команды {command}: {e}"
            my_logging.error(error_msg)
            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE,
                                     json.dumps({"status": "error", "message": error_msg}))

    async def get_user_traffic(self, user_ip: str) -> Dict:
        """Возвращает информацию о трафике пользователя WireGuard."""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "exec", "-i", "wg-easy", "wg", "show", "wg0", "dump",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f"Ошибка выполнения wg show wg0 dump: {stderr.decode().strip()}")

            for line in stdout.decode().splitlines():
                parts = line.split()
                if len(parts) >= 7 and user_ip in parts[3]:
                    return {
                        "transfer_received": parts[5],
                        "transfer_sent": parts[6],
                        "latest_handshake": parts[4]
                    }
        except Exception as e:
            my_logging.error(f"Ошибка получения трафика пользователя WireGuard: {e}")
        return {"transfer_received": "0", "transfer_sent": "0", "latest_handshake": "Never"}

    async def get_user_enable_status(self, user_ip: str) -> bool:
        try:
            async with aiofiles.open(ServerSettings.PATH_PRIMARY_WG_JSON, mode="r", encoding="utf-8") as file:
                wg_config = json.loads(await file.read())
            for client in wg_config.get("clients", {}).values():
                if client.get("address") == user_ip:
                    return client.get("enabled", False)
        except Exception as e:
            my_logging.error(f"Ошибка получения состояния пользователя WireGuard: {e}")
        return False

    @staticmethod
    async def restart_wireguard():
        """
        Перезапуск WireGuard, если он запущен в Docker (wg-easy).
        """
        try:
            subprocess.run(["docker", "restart", "wg-easy"], check=True)
            my_logging.info("✅ WireGuard (wg-easy) успешно перезапущен.")
            return {"status": "success", "message": "WireGuard restarted"}
        except subprocess.CalledProcessError as e:
            my_logging.error(f"❌ Ошибка при перезапуске WireGuard: {e}")
            return {"status": "error", "message": str(e)}

    async def process_delete_user(self, task_data: Dict):
        """
        Удаление пользователя из файлов конфигурации WireGuard (wg0.conf, wg0.json)
        по IP-адресу и перезапуск WireGuard.
        """
        user_ip = task_data.get("user_ip")
        chat_id = task_data.get("chat_id")
        PATH_WG_CONF = Path(ServerSettings.PATH_PRIMARY_WG_CONFIG)
        PATH_WG_JSON = Path(ServerSettings.PATH_PRIMARY_WG_JSON)

        if not user_ip:
            my_logging.error("❌ Ошибка: не указан IP-адрес пользователя для удаления.")
            return {"status": "error", "message": "user_ip is required"}

        my_logging.info(f"🔍 Поиск и удаление пользователя с IP {user_ip}")

        try:
            # 1️⃣ Читаем текущий wg0.json
            if not PATH_WG_JSON.exists():
                my_logging.error("❌ Ошибка: Файл wg0.json не найден!")
                return {"status": "error", "message": "wg0.json not found"}

            with PATH_WG_JSON.open("r", encoding="utf-8") as json_file:
                wg_data = json.load(json_file)

            # 2️⃣ Проверяем, есть ли клиенты в JSON
            clients = wg_data.get("clients")
            if not clients or not isinstance(clients, dict):
                my_logging.error("❌ Ошибка: В файле wg0.json отсутствует раздел 'clients' или он поврежден.")
                return {"status": "error", "message": "Invalid wg0.json structure"}

            # 3️⃣ Ищем пользователя в JSON
            user_id = None
            for client_id, client_info in clients.items():
                if client_info.get("address") == user_ip:
                    user_id = client_id
                    break

            if not user_id:
                my_logging.warning(f"⚠️ Пользователь с IP {user_ip} не найден в wg0.json")
                return {"status": "not_found", "message": "User not found in wg0.json"}

            # 4️⃣ Удаляем пользователя из JSON
            del wg_data["clients"][user_id]

            # 5️⃣ Записываем обновленный wg0.json
            with PATH_WG_JSON.open("w", encoding="utf-8") as json_file:
                json.dump(wg_data, json_file, indent=4)

            my_logging.info(f"✅ Пользователь {user_id} удалён из wg0.json")

            # 6️⃣ Читаем текущий wg0.conf
            if not PATH_WG_CONF.exists():
                my_logging.error("❌ Ошибка: Файл wg0.conf не найден!")
                return {"status": "error", "message": "wg0.conf not found"}

            with PATH_WG_CONF.open("r", encoding="utf-8") as conf_file:
                conf_lines = conf_file.readlines()

            # 7️⃣ Удаляем блок пользователя из wg0.conf
            new_conf_lines = []
            skip_lines = False
            found_user = False

            for line in conf_lines:
                if f"AllowedIPs = {user_ip}/32" in line:
                    skip_lines = True  # Начало блока пользователя
                    found_user = True
                    continue
                if skip_lines and line.strip() == "":
                    skip_lines = False  # Конец блока пользователя
                    continue
                if not skip_lines:
                    new_conf_lines.append(line)

            if not found_user:
                my_logging.warning(f"⚠️ Пользователь с IP {user_ip} не найден в wg0.conf")
                return {"status": "not_found", "message": "User not found in wg0.conf"}

            # 8️⃣ Записываем обновленный wg0.conf
            with PATH_WG_CONF.open("w", encoding="utf-8") as conf_file:
                conf_file.writelines(new_conf_lines)

            my_logging.info(f"✅ Пользователь {user_id} удалён из wg0.conf")

            # 9️⃣ Применение изменений через Docker `wg syncconf`
            command = [
                "docker", "exec", "wg-easy", "sh", "-c",
                "wg-quick strip /etc/wireguard/wg0.conf > /tmp/wg0_stripped.conf && "
                "wg syncconf wg0 /tmp/wg0_stripped.conf && "
                "touch /etc/wireguard/wg0.json"
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = f"❌ Ошибка при применении конфигурации WireGuard: {stderr.decode().strip()}"
                my_logging.error(error_msg)
                return {"status": "error", "message": error_msg}

            my_logging.info(f"✅ Изменения WireGuard успешно применены: {stdout.decode().strip()}")

            # 🔟 Подтверждение удаления в Redis
            redis_client = await ServerSettings.get_redis_client()
            result = {
                "status": "success",
                "task_type": "result_delete_user",
                "chat_id": chat_id,
                "protocol": "wireguard",
                "user_ip": user_ip,
                "action": "deleted"
            }

            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.info(f"✅ Удаление пользователя завершено. Результат: {result}")

            return {"status": "success", "message": f"User {user_id} deleted and WireGuard config updated"}


        except Exception as e:
            my_logging.error(f"❌ Ошибка при удалении пользователя: {e}")
            return {"status": "error", "message": str(e)}

    async def creating_user(self, task_data: Dict, count_users=5):
        """
        🏗 Создание нового пользователя WireGuard с добавлением в конфигурацию и синхронизацией без перезагрузки.
        """
        server_ip = ServerSettings.SERVER_IP
        server_name = ServerSettings.SERVER_NAME
        server_public_key = ServerSettings.SERVER_PUBLIC_KEY_WG
        PATH_WG_CONF = Path(ServerSettings.PATH_PRIMARY_WG_CONFIG)
        PATH_WG_JSON = Path(ServerSettings.PATH_PRIMARY_WG_JSON)


        created_users = []

        try:
            # 1️⃣ Читаем текущий wg0.json
            if not PATH_WG_JSON.exists():
                my_logging.error("❌ Ошибка: Файл wg0.json не найден!")
                return {"status": "error", "message": "wg0.json not found"}

            async with aiofiles.open(PATH_WG_JSON, mode="r", encoding="utf-8") as json_file:
                wg_data = json.loads(await json_file.read())

            clients = wg_data.get("clients", {})
            existing_ips = {client["address"] for client in clients.values()}

            # 2️⃣ Генерация новых пользователей
            for _ in range(count_users):
                new_ip = self.generate_next_ip(existing_ips)
                if not new_ip:
                    my_logging.warning("Достигнуто максимальное количество IP-адресов для WireGuard.")
                    break

                user_id = str(uuid4())
                private_key, public_key = await self.generate_keys()
                pre_shared_key = await self.generate_pre_shared_key()
                user_name = await self.generate_wireguard_username()
                if not user_name:
                    my_logging.warning("Достигнуто максимальное количество имен пользователей для WireGuard.")
                    break

                created_at = datetime.utcnow().isoformat()

                # 🔹 Добавление нового пользователя в wg0.json
                new_user = {
                    "id": user_id,
                    "name": user_name,
                    "address": new_ip,
                    "privateKey": private_key,
                    "publicKey": public_key,
                    "preSharedKey": pre_shared_key,
                    "createdAt": created_at,
                    "updatedAt": created_at,
                    "enabled": True
                }
                wg_data["clients"][user_id] = new_user
                existing_ips.add(new_ip)

                created_users.append({
                    "user_id": user_id,
                    "name": user_name,
                    "address": new_ip,  # клиентский IP
                    "private_key": private_key,
                    "public_key": public_key,
                    "pre_shared_key": pre_shared_key,
                    "server_public_key": server_public_key,
                    "endpoint": f"{ServerSettings.SERVER_IP}:51820",  # или переменной
                    "dns": "1.1.1.1"
                })

                # 3️⃣ Сортируем клиентов по возрастанию IP
                wg_data["clients"] = {
                    k: v for k, v in sorted(wg_data["clients"].items(), key=lambda item: int(item[1]["address"].split(".")[-1]))
                }

                # 4️⃣ Записываем обновленный wg0.json
                async with aiofiles.open(PATH_WG_JSON, mode="w", encoding="utf-8") as json_file:
                    await json_file.write(json.dumps(wg_data, indent=4))

                # 5️⃣ Обновляем wg0.conf
                await self.update_wireguard_conf(wg_data)

            # 6️⃣ Применяем конфигурацию без перезагрузки
            await self.apply_wireguard_changes()
            await self.restart_wireguard()

            # 7️⃣ Отправка результата в Redis
            redis_client = await ServerSettings.get_redis_client()
            result = {
                "status": "success",
                "server_id": server_ip,
                "server_name": server_name,
                "task_type": "result_create_user",
                "protocol": "wireguard",
                "count_users": len(created_users),
                "created_users": created_users,
                "action": "created_batch"
            }
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.info(f"🌟 Создание {len(created_users)} пользователей WireGuard завершено: {result}")

            return result

        except Exception as e:
            redis_client = await ServerSettings.get_redis_client()
            result = {
                "status": "error",
                "server_id": server_ip,
                "server_name": server_name,
                "task_type": "result_create_user",
                "protocol": "wireguard",
                "message": str(e)
            }
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.error(f"❌ Ошибка при создании пользователей WireGuard: {e}")
            return result

    async def generate_wireguard_username(self):
        """
        🔄 Генерирует минимальное доступное уникальное имя WireGuard в формате <номер>_free
        начиная с server_number и до server_number + 1000.
        """
        server_name = ServerSettings.SERVER_NAME
        parts = server_name.split("_")
        numbers = [word for word in parts if word.isdigit()]
        server_number = sum(int(word) for word in numbers) if numbers else 99000  # Значение по умолчанию

        my_logging.info(f"📌 Определен номер сервера: {server_number}")

        PATH_WG_JSON = Path(ServerSettings.PATH_PRIMARY_WG_JSON)

        async with aiofiles.open(PATH_WG_JSON, mode="r", encoding="utf-8") as json_file:
            wg_data = json.loads(await json_file.read())

        clients = wg_data.get("clients", {})
        existing_numbers = {
            int(client["name"].split("_")[0])
            for client in clients.values()
            if client.get("name", "").endswith("_free") and client.get("name", "").split("_")[0].isdigit()
        }

        for new_number in range(server_number, server_number + 1000):
            if new_number not in existing_numbers:
                new_name = f"{new_number}_free"
                my_logging.info(f"Сгенерировано имя: {new_name}")
                return new_name

        my_logging.error("❌ Не удалось сгенерировать уникальное имя WireGuard.")
        return None

    async def update_wireguard_conf(self, wg_data):
        """
        🔄 Обновляет wg0.conf, сортируя пользователей по IP.
        """
        PATH_WG_CONF = Path(ServerSettings.PATH_PRIMARY_WG_CONFIG)

        async with aiofiles.open(PATH_WG_CONF, mode="r", encoding="utf-8") as conf_file:
            conf_lines = await conf_file.readlines()

        # Удаляем все существующие [Peer] секции
        conf_header = []
        for line in conf_lines:
            if "[Peer]" in line:
                break
            conf_header.append(line)

        sorted_clients = sorted(wg_data["clients"].values(), key=lambda c: int(c["address"].split(".")[-1]))

        new_conf_lines = conf_header
        for client in sorted_clients:
            new_conf_lines.extend([
                f"\n# Client: {client['name']} ({client['id']})\n",
                "[Peer]\n",
                f"PublicKey = {client['publicKey']}\n",
                f"PresharedKey = {client['preSharedKey']}\n",
                f"AllowedIPs = {client['address']}/32\n"
            ])

        async with aiofiles.open(PATH_WG_CONF, mode="w", encoding="utf-8") as conf_file:
            await conf_file.writelines(new_conf_lines)

    async def apply_wireguard_changes(self):
        """
        🔄 Применяет изменения в WireGuard без перезагрузки.
        """
        command = [
            "docker", "exec", "wg-easy",
            "sh", "-c",
            "wg-quick strip /etc/wireguard/wg0.conf > /tmp/wg0_stripped.conf && "
            "wg syncconf wg0 /tmp/wg0_stripped.conf && "
            "touch /etc/wireguard/wg0.json"
        ]
        subprocess.run(command, check=True)
        my_logging.info("✅ WireGuard конфигурация обновлена без перезагрузки.")

    async def get_count_true_user(self) -> int:
        try:
            path_json = Path(ServerSettings.PATH_PRIMARY_WG_JSON)

            if not path_json.exists():
                my_logging.warning("wg0.json не найден.")
                return 0

            async with aiofiles.open(path_json, mode="r", encoding="utf-8") as f:
                data = json.loads(await f.read())

            clients = data.get("clients", {})
            enabled_users = [c for c in clients.values() if c.get("enabled") is True]
            count_enabled = len(enabled_users)

            my_logging.info(f"Количество активных пользователей (enabled=True): {count_enabled}")
            return count_enabled

        except Exception as e:
            my_logging.error(f"Ошибка при подсчёте активных пользователей WireGuard: {e}")
            return 0

    @staticmethod
    async def generate_keys():
        """
        🔑 Генерирует приватный и публичный ключи для нового пользователя WireGuard.
        """
        private_key = subprocess.run(["wg", "genkey"], capture_output=True, text=True).stdout.strip()
        public_key = subprocess.run(["wg", "pubkey"], input=private_key, capture_output=True, text=True).stdout.strip()
        return private_key, public_key

    @staticmethod
    def generate_next_ip(existing_ips: set) -> str:
        """
        🛜 Генерирует следующий доступный IP-адрес в диапазоне 10.8.0.X.
        """
        base_ip = "10.8.0."
        for i in range(2, 255):  # Начинаем с 10.8.0.2
            new_ip = f"{base_ip}{i}"
            if new_ip not in existing_ips:
                return new_ip
        return None

    @staticmethod
    async def generate_pre_shared_key():
        """Генерирует PreSharedKey (PSK) для WireGuard."""
        try:
            process = await asyncio.create_subprocess_exec(
                "wg", "genpsk",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"Ошибка при генерации PSK: {stderr.decode().strip()}")

            return stdout.decode().strip()

        except Exception as e:
            print(f"Ошибка генерации PSK: {e}")
            return None