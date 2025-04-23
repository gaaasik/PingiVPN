class ServerModel:
    def __init__(self, data: dict):
        self.name = data.get("name")
        self.country = data.get("country")
        self.address = data.get("address")
        self.xui_url = data.get("3X_UI", "").strip()
        self.username = data.get("username")
        self.passwords = data.get("passwords", {})

    @property
    def login(self):
        return self.passwords.get("login")

    @property
    def password(self):
        return self.passwords.get("password")