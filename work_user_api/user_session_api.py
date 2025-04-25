from urllib.parse import urljoin

from work_user_api.decryptor import decrypt_json_file, logger
from work_user_api.models import Server, ServerPassword
import json
import requests

from work_user_api.server_model import ServerModel


class EnableToggle:
    def __init__(self, server: Server, uuid_id: str):
        self.server = server
        self.uuid_id = uuid_id
        self.session = requests.Session()

    def _login(self) -> bool:
        login_url = f"{self.server.xui_url}login"
        logger.info(f"[POST] Авторизация в XUI: {login_url}")
        try:
            response = self.session.post(
                login_url,
                json={
                    "username": self.server.login,
                    "password": self.server.password
                },
                verify=False
            )
            logger.info(f"[LOGIN STATUS] {response.status_code} - {response.text[:100]}")

            # Сохраняем куки после логина
            self.session.cookies.update(response.cookies)

            return response.status_code == 200
        except Exception as e:
            logger.exception("❌ Ошибка при логине в XUI")
            return False

    def _get_inbound(self) -> list:
        inbound_url = f"{self.server.xui_url}xui/inbound/list"
        logger.info(f"[GET] Получаем список пользователей: {inbound_url}")
        try:
            response = self.session.get(inbound_url, verify=False)
            if not response.text:
                logger.error(f"[ERROR] Сервер вернул пустой ответ на {inbound_url}")
                return []
            try:
                return response.json().get("obj", [])
            except json.JSONDecodeError:
                logger.error(f"[ERROR] Ответ сервера не является JSON: {response.status_code} — {response.text[:100]}")
                return []
        except Exception as e:
            logger.exception("❌ Ошибка при получении списка пользователей")
            return []

    def set(self, state: bool):
        if not self._login():
            logger.error("❌ Логин не выполнен. Операция отменена.")
            return False
        inbounds = self._get_inbound()
        for inbound in inbounds:
            clients = json.loads(inbound["settings"]).get("clients", [])
            for client in clients:
                if client["id"] == self.uuid_id:
                    client["enable"] = state
                    data = {
                        "id": inbound["id"],
                        "settings": json.dumps({"clients": clients})
                    }
                    url = f"{self.server.xui_url}/panel/api/inbounds/updateClient/{self.uuid_id}"
                    response = self.session.post(url, json=data, verify=False)
                    return response.status_code == 200
        return False

    def get(self) -> bool:
        if not self._login():
            login = self.server.get_password("login")
            password = self.server.get_password("password")
            return False

        inbounds = self._get_inbound()
        for inbound in inbounds:
            clients = json.loads(inbound["settings"]).get("clients", [])
            for client in clients:
                if client["id"] == self.uuid_id:
                    return client.get("enable", False)
        return False


class UserSessionAPI:
    def __init__(self, ip_server: str, uuid_id: str):
        self.uuid_id = uuid_id
        self.server = self._get_server_by_ip(ip_server)
        if not self.server:
            raise ValueError(f"Сервер с IP {ip_server} не найден.")
        self.enable = EnableToggle(self.server, self.uuid_id)

    def _get_server_by_ip(self, ip_server):
        data = decrypt_json_file()
        for srv in data:
            if srv.get("address") == ip_server:
                return ServerModel(srv)
        raise ValueError(f"Server with IP {ip_server} not found.")