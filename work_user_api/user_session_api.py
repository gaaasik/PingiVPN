from work_user_api.decryptor import decrypt_json_file
from work_user_api.models import Server, ServerPassword
import json
import requests


class EnableToggle:
    def __init__(self, server: Server, uuid_id: str):
        self.server = server
        self.uuid_id = uuid_id
        self.session = requests.Session()

    def _login(self):
        login_url = f"{self.server.xui_url}/login"
        try:
            resp = self.session.post(login_url, data={
                "username": self.server.passwords.login,
                "password": self.server.passwords.password
            }, verify=False)
            return resp.status_code == 200
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def _get_inbound(self):
        list_url = f"{self.server.xui_url}/panel/api/inbounds/list"
        response = self.session.get(list_url, verify=False)
        return response.json().get("obj", [])

    def set(self, state: bool) -> bool:
        if not self._login():
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

    def _get_server_by_ip(self, ip: str) -> Server:
        data = decrypt_json_file()
        for srv in data.get("servers", []):
            if srv["address"] == ip:
                return Server(
                    name=srv["name"],
                    country=srv["country"],
                    address=srv["address"],
                    xui_url=srv.get("3X_UI", "").strip(),
                    username=srv["username"],
                    passwords=ServerPassword(
                        login=srv["passwords"]["login"],
                        password=srv["passwords"]["password"],
                        root_password=srv["passwords"]["root password"]
                    )
                )
        return None