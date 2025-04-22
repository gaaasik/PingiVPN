import requests
from work_user_api.models import Server
import json

class XUIApiClient:
    def __init__(self, server: Server):
        self.server = server
        self.session = requests.Session()

    def login(self) -> bool:
        url = f"{self.server.xui_url}/login"
        data = {
            "username": self.server.passwords.login,
            "password": self.server.passwords.password
        }
        try:
            resp = self.session.post(url, data=data, verify=False)
            return resp.status_code == 200
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def toggle_user(self, email: str, enable: bool) -> bool:
        if not self.login():
            return False

        list_url = f"{self.server.xui_url}/panel/api/inbounds/list"
        update_base = f"{self.server.xui_url}/panel/api/inbounds/updateClient"
        headers = {"Accept": "application/json"}

        resp = self.session.get(list_url, headers=headers, verify=False)
        inbounds = resp.json()["obj"]

        for inbound in inbounds:
            settings = json.loads(inbound["settings"])
            clients = settings.get("clients", [])
            for c in clients:
                if c["email"] == email:
                    c["enable"] = enable
                    data = {
                        "id": inbound["id"],
                        "settings": json.dumps({"clients": clients})
                    }
                    update_url = f"{update_base}/{c['id']}"
                    r = self.session.post(update_url, json=data, headers=headers, verify=False)
                    return r.status_code == 200
        return False
