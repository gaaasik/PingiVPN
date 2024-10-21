class Server_cl:
    def __init__(self, server_data: dict, user):
        # Инициализация всех полей, переданных в JSON
        self.name_server = Field('name_server', server_data.get("name_server", None), self)
        self.country_server = Field('country_server', server_data.get("country_server", None), self)
        self.server_1_ip = Field('server_1_ip', server_data.get("server_1_ip", None), self)
        self.user_ip = Field('user_ip', server_data.get("user_ip", None), self)
        self.name_conf = Field('name_conf', server_data.get("name_conf", None), self)
        self.enable = Field('enable', server_data.get("enable", None), self)
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
            "server_1_ip": self.server_1_ip.get(),
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

class Field:
    def __init__(self, name, value, server):
        self.name = name  # Название поля (например, 'status_key')
        self.value = value  # Текущее значение поля
        self.server = server  # Ссылка на объект Server_cl

    def get(self):
        return self.value

    async def set(self, new_value):
        """Обновление значения поля и данных в базе через объект Server_cl."""
        self.value = new_value
        setattr(self.server, f"_{self.name}", new_value)
        await self.server.update_in_db()  # Обновление данных в базе через объект Server_cl
