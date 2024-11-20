
# Проверка подписки через Telegram API getChatMember
async def check_subscription_channel(chat_id, bot):
    status = await bot.get_chat_member("@pingi_hub", chat_id)
    if status.status in ["member", "administrator", "creator"]:
        return True
    return False
