from flask import Flask, Response, abort
import asyncio
from models.UserCl import UserCl

app = Flask(__name__)

@app.route("/sub/<int:chat_id>")
def get_subscription(chat_id):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        urls = loop.run_until_complete(get_vless_urls(chat_id))
    except Exception as e:
        print(f"❌ Ошибка при получении конфигов для chat_id {chat_id}: {e}")
        abort(500)

    if not urls:
        return Response("Нет активных VLESS ключей", status=404)

    return Response("\n".join(urls), mimetype="text/plain")

async def get_vless_urls(chat_id: int):
    user = await UserCl.load_user(chat_id)
    if not user or not user.servers:
        return []

    result = []
    for server in user.servers:
        if await server.name_protocol.get() == "vless":
            url = await server.url_vless.get()
            result.append(url)
    return result

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
