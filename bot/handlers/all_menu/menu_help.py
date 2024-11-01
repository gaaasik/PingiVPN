# bot/handlers/help_menu.py


from aiogram import Router, types, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
router = Router()

# Текст для помощи
help_text_message = (
    f"📚 *Помощь и поддержка*\n"
    "Напишите нам и мы обязательно вам поможем и поддержим:"
)

# Клавиатура с вариантами вопросов
def help_options_keyboard():
    buttons = [
        # [
        #     InlineKeyboardButton(text="🚀 Как подключиться к VPN?", callback_data="help_connect_vpn"),
        # ],
        # [
        #     InlineKeyboardButton(text="🛠️ Что делать, если VPN не работает?", callback_data="help_vpn_not_working"),
        # ],
        [
            InlineKeyboardButton(text="💬 Задать вопрос", callback_data="help_ask_question"),
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Универсальный обработчик для команды "/support" и кнопки "help"
@router.message(Command("support"))
@router.callback_query(F.data == "help")
async def handle_support(event: types.Message | types.CallbackQuery):
    if isinstance(event, types.Message):
        await event.answer(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
        await event.answer()  # Подтверждаем callback_query