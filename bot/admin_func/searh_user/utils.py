import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional

from models.ServerCl import ServerCl


async def user_to_json(user, db_path: str) -> dict:
    """Конвертирует объект пользователя и его серверов в JSON."""
    user_data = {
        "chat_id": user.chat_id,
        "user_name": await user.user_name_full.get(),
        "login": await user.user_login.get(),
        "email": await user.email.get(),
        "registration_date": await user.registration_date.get(),
        "referral_old_chat_id": await user.referral_old_chat_id.get(),
        "device": await user.device.get(),
        "is_subscribed_on_channel": await user.is_subscribed_on_channel.get(),
        "days_since_registration": await user.days_since_registration.get(),
        "count_key": await user.count_key.get(),
        "value_key": None  # Здесь будут данные серверов
    }

    try:
        async with aiosqlite.connect(db_path) as db:
            query = "SELECT value_key FROM users_key WHERE chat_id = ?"
            async with db.execute(query, (user.chat_id,)) as cursor:
                result = await cursor.fetchone()
                if result and result[0]:  # Проверяем, что результат не пустой
                    try:
                        user_data["value_key"] = json.loads(result[0])
                    except json.JSONDecodeError:
                        logging.error(f"Ошибка декодирования JSON для chat_id {user.chat_id}")
                        user_data["value_key"] = []
    except Exception as e:
        logging.error(f"Ошибка при обработке user_to_json: {e}")
        user_data["value_key"] = []

    return user_data


async def format_user_data(user_data: dict) -> str:
    """Форматирует данные пользователя и его серверов для красивого вывода."""
    if not user_data:
        return "Данные пользователя не найдены."

    # Форматируем основные поля пользователя
    formatted_data = [
        f"<b>👤 Chat ID:</b> {user_data.get('chat_id', 'Не указано')}",
        f"<b>👤 Имя пользователя:</b> {user_data.get('user_name', 'Не указано')}",
        f"<b>🔑 Логин:</b> {user_data.get('login', 'Не указано')}",
        f"<b>📧 Email:</b> {user_data.get('email', 'Не указано')}",
        f"<b>📅 Дата регистрации:</b> {user_data.get('registration_date', 'Не указано')}",
        f"<b>🆔 Реферальный ID:</b> {user_data.get('referral_old_chat_id', 'Не указано')}",
        f"<b>📱 Устройство:</b> {user_data.get('device', 'Не указано')}",
        f"<b>📢 Подписка на канал:</b> {'✅ Да' if user_data.get('is_subscribed_on_channel') else '❌ Нет'}",
        f"<b>📆 Дни с момента регистрации:</b> {user_data.get('days_since_registration', 'Не указано')}",

    ]

    # Форматируем данные серверов
    value_key = user_data.get("value_key", [])
    if isinstance(value_key, list) and value_key:
        for i, server in enumerate(value_key, 1):
            formatted_data.extend([
                f"\n<b>🖥️ Сервер {i}:</b>",
                f"  🌍 <b>Страна сервера:</b> {server.get('country_server', 'Не указано')}",
                f"  🕒 <b>Дата создания ключа :</b> {server.get('date_creation_key', 'Не указано')}",
                f"  ⏳ <b>Дата окончания:</b> {server.get('date_key_off', 'Не указано')}",
                # f"  📥 <b>Трафик (загрузка):</b> {server.get('traffic_down', '0')} MB",
                # f"  📤 <b>Трафик (отдача):</b> {server.get('traffic_up', '0')} MB",
                f"  💻 <b>Имя сервера:</b> {server.get('name_server', 'Не указано')}",
                f"  🛡️ <b>Протокол:</b> {server.get('name_protocol', 'Не указано')}",
                f"  🖥️ <b>IP сервера:</b> {server.get('server_ip', 'Не указано')}",
                f"  🔑 <b>UUID:</b> {server.get('uuid_id', 'Не указано')}",
                f"  ⚙️ <b>Статус:</b> {server.get('status_key', 'Не указано')}",
                f"  🟢 <b>Статус аккаунта :</b> {'✅ Включен' if server.get('enable') else '❌ Выключен'}",
                f"  💰 <b>Дата оплаты ключа:</b> {server.get('date_payment_key', 'Не указано')}",
                f"  💳 <b>Кол-во оплат:</b> {server.get('has_paid_key', 'Не указано')}",
                f"  📧 <b>Email ключа:</b> {server.get('email_key', 'Не указано')}",
                f"  🌐 <b>URL VLESS:</b> <pre>{server.get('url_vless', 'Не указано')}</pre>",
                f"  📡 <b>IP пользователя:</b> {server.get('user_ip', 'Не указано')}",
            ])
    else:
        formatted_data.append("\n<b>🚫 Серверы:</b> Нет информации о серверах.")

    return "\n".join(formatted_data)


async def format_history_key(key: ServerCl, i: int = 0) -> str:
    """Форматирует данные одного ключа из history_key_list для вывода пользователю."""
    if not key:
        return "<b>🚫 Серверы:</b> Нет информации о серверах."

    return "\n".join([
        f"\n<b>🖥️ Ключ {i+1}:</b>",
        f"  🌍 <b>Страна сервера:</b> {await key.country_server.get()}",
        f"  🕒 <b>Дата создания ключа :</b> {await key.date_creation_key.get()}",
        f"  ⏳ <b>Дата окончания:</b> {await key.date_key_off.get()}",
        f"  📥 <b>Трафик (загрузка):</b> {await key.traffic_up.get()} MB",
        f"  📤 <b>Трафик (отдача):</b> {await key.traffic_down.get()} MB",
        f"  💻 <b>Имя сервера:</b> {await key.name_server.get()}",
        f"  🛡️ <b>Протокол:</b> {await key.name_protocol.get()}",
        f"  🖥️ <b>IP сервера:</b> {await key.server_ip.get()}",
        f"  🔑 <b>UUID:</b> {await key.uuid_id.get()}",
        f"  ⚙️ <b>Статус:</b> {await key.status_key.get()}",
        f"  🟢 <b>Статус аккаунта :</b> {'✅ Включен' if await key.enable.get() else '❌ Выключен'}",
        f"  💰 <b>Дата оплаты ключа:</b> {await key.date_payment_key.get()}",
        f"  💳 <b>Кол-во оплат:</b> {await key.has_paid_key.get()}",
        f"  📧 <b>Email ключа:</b> {await key.email_key.get()}",
        f"  🌐 <b>URL VLESS:</b> {await key.url_vless.get()}",
        f"  📡 <b>IP пользователя:</b> {await key.user_ip.get()}",
    ])