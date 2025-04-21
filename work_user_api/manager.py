from work_user_api.decryptor import load_decrypted_servers
from work_user_api.models import Server, ServerList, ServerPassword
from work_user_api.xui_api_client import XUIApiClient

def enable_user(server_name: str, email: str):
    data = load_decrypted_servers()
    servers = ServerList([Server(
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
    ) for s in data["servers"]])

    server = servers.get_by_name(server_name)
    if not server:
        print(f"⚠️ Server '{server_name}' not found.")
        return False

    client = XUIApiClient(server)
    success = client.toggle_user(email=email, enable=True)
    print("✅ Enabled" if success else "❌ Failed to enable")
    return success