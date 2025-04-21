import requests
from work_user_api.models import Server
import logging

class XUIApiClient:
    def __init__(self, server: Server):
        self.server = server
        self.session = requests.Session()
        self.token = None

    def login(self):
        url = f"{self.server.xui_url}/login"
        data = {
            "username": self.server.passwords.login,
            "password": self.server.passwords.password
        }
        try:
            response = self.session.post(url, data=data, verify=False)
            response.raise_for_status()
            self.token = response.cookies.get("session")
            return True
        except Exception as e:
            logging.error(f"❌ Login failed for {self.server.name}: {e}")
            return False

    def toggle_user(self, email: str, enable: bool):
        if not self.login():
            return False

        headers = {"Accept": "application/json"}
        list_url = f"{self.server.xui_url}/panel/api/inbounds/list"
        update_base = f"{self.server.xui_url}/panel/api/inbounds/updateClient"

        inbounds = self.session.get(list_url, headers=headers, verify=False).json()["obj"]
        for inbound in inbounds:
            settings = inbound.get("settings", "")
            if email in settings:
                import json, uuid
                settings_json = json.loads(settings)
                clients = settings_json.get("clients", [])
                for c in clients:
                    if c.get("email") == email:
                        c["enable"] = enable
                        data = {"id": inbound["id"], "settings": json.dumps({"clients": clients})}
                        update_url = f"{update_base}/{c['id']}"
                        response = self.session.post(update_url, json=data, headers=headers, verify=False)
                        return response.ok
        return False