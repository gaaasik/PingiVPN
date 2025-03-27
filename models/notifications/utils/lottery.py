from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot_instance import bot
from bot.handlers.admin import ADMIN_CHAT_IDS

router = Router()
entries = {}

def get_lottery_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Продлить доступ", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_feedback"),
             InlineKeyboardButton(text="🎁 Поделиться с другом", callback_data="show_referral_link")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


@router.callback_query(F.data == "lottery_entry")
async def handle_lottery_entry(callback: CallbackQuery):
    user_id = callback.from_user.id
    entries[user_id] = entries.get(user_id, 0) + 1
    keyboard = get_lottery_keyboard()

    await callback.message.edit_text(
        "🎉 Чтобы участвовать в розыгрыше бесплатного доступа от 1 до 3 месяцев:\n\n"
        "📨 Подключите к боту как минимум <b>3 друзей</b>\n"
        "📢 Опубликуйте <b>историю в Telegram</b> с отметкой нашего бота.\n\n"
        "После этого вы автоматически участвуете в розыгрыше призов! 🎁",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    for admin_id in ADMIN_CHAT_IDS:
        await bot.send_message(admin_id, f"🎲 Пользователь {user_id} участвует в розыгрыше!")
