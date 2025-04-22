from work_user_api.models import Server, ServerPassword, ServerList
from work_user_api.decryptor import decrypt_json_file
from work_user_api.xui_api_client import XUIApiClient

def get_all_servers() -> ServerList:
    raw = decrypt_json_file()
    servers = []
    for s in raw["servers"]:
        servers.append(Server(
            name=s["name"],
            country=s["country"],
            address=s["address"],
            xui_url=s.get("3X_UI", "").strip(),
            username=s["username"],
            passwords=ServerPassword(
                login=s["passwords"]["login"],
                password=s["passwords"]["password"],
                root_password=s["passwords"]["root password"]
            )
        ))
    return ServerList(servers)

def enable_user(server_name: str, email: str):
    servers = get_all_servers()
    server = servers.get_by_name(server_name)
    if not server:
        print("🚫 Server not found")
        return False
    return XUIApiClient(server).toggle_user(email, True)

def disable_user(server_name: str, email: str):
    servers = get_all_servers()
    server = servers.get_by_name(server_name)
    if not server:
        print("🚫 Server not found")
        return False
    return XUIApiClient(server).toggle_user(email, False)