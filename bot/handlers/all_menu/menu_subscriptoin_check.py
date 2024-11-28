
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

from bot.handlers.admin import send_admin_log
from models.UserCl import UserCl
router = Router()


PINGI_CHANNEL = "Ping_hub"

# Кнопка для перехода на канал и кнопка для проверки подписки
def subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти на канал", url="https://t.me/pingi_hub")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="connect_vpn")]
    ])
    return keyboard

# Кнопка для действия после попытки подписки
def subscribe_keyboard_if_us_action():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти на канал", url=f"https://t.me/pingi_hub")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="i_am_subscribed")]
    ])
    return keyboard

# Текст сообщения
def subscription_message():
    return (
        f"📢 <b>Уважаемый пользователь!</b>\n\n"
        f"Пожалуйста, подпишитесь на наш канал <a href='https://t.me/{PINGI_CHANNEL}'>@Ping_hub</a> 🐧,\n"
        "чтобы продолжить пользоваться VPN.\n\n"
        "Это поможет нам поддерживать сервис\n"
        "и радовать вас новыми функциями. 🚀"
    )
@router.callback_query(lambda c: c.data == "i_am_subscribed")
async def handle_subscription_check(callback: types.CallbackQuery):
    """
    Обработчик для кнопки "✅ Я подписался".
    Проверяет, подписан ли пользователь, и отправляет соответствующее сообщение.
    """
    chat_id = callback.from_user.id

    # Проверяем подписку пользователя
    user = await UserCl.load_user(chat_id)
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден в базе данных.")
        await callback.answer()
        return

    is_subscribed = await user.is_subscribed_on_channel.get()

    if is_subscribed:
        # Если пользователь подписан
        await callback.message.answer(
            "Спасибо, что вы с нами! 🎉 В канале мы будем держать вас в курсе важных новостей."
        )
        await send_admin_log(callback.bot, f"Пользователь {chat_id} подписался и нажал 'я подписался'.")
    else:
        # Если пользователь не подписан, отправляем новое сообщение
        await callback.message.answer(
            subscription_message(),
            reply_markup=subscribe_keyboard_if_us_action(), parse_mode="HTML"
        )
        await send_admin_log(callback.bot, f"Пользователь {chat_id} нажал 'я подписался', но не подписан.")

    # Уведомляем Telegram об успешной обработке callback, чтобы убрать значок загрузки
    await callback.answer()
