from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ServerPassword:
    login: str
    password: str
    root_password: str

@dataclass
class Server:
    name: str
    country: str
    address: str
    xui_url: Optional[str]
    username: str
    passwords: ServerPassword

@dataclass
class ServerList:
    servers: List[Server]

    def get_by_name(self, name: str) -> Optional[Server]:
        return next((s for s in self.servers if s.name == name), None)


@dataclass
class VPNUser:
    id: str
    email: str
    enable: bool
    expiry_time: int  # timestamp (ms)