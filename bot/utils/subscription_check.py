from datetime import datetime, timedelta
from bot.database.db import update_user_subscription_status, get_last_subscription_check, update_last_subscription_check


# Проверка подписки через Telegram API getChatMember
async def check_subscription_channel(chat_id, bot):
    status = await bot.get_chat_member("@pingi_hub", chat_id)
    if status.status in ["member", "administrator", "creator"]:
        return True
    return False


async def delete_subscription_channel_message(callback_query):
    """
    Удаляет сообщение с просьбой подписаться, если оно существует.
    """
    try:
        await callback_query.message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")


# Проверка, нужно ли повторно проверять подписку (раз в 3 дня)
async def should_check_subscription(chat_id):
    last_check = await get_last_subscription_check(chat_id)

    if last_check:
        last_check_dt = datetime.strptime(last_check.split('.')[0], '%Y-%m-%d %H:%M:%S')
        return datetime.now() - last_check_dt > timedelta(days=3)

    return True


# Обновление статуса подписки и времени последней проверки
async def update_subscription_status(chat_id, bot):
    if await check_subscription_channel(chat_id, bot):
        await update_user_subscription_status(chat_id, True)
        await update_last_subscription_check(chat_id)
        return True
    return False
