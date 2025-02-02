import logging
from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Список администраторов
ADMIN_CHAT_IDS = [456717505, 1388513042, 7032840268, 6720032062]  # Укажи ID администраторов

# Создаем реплай-клавиатуру с кнопкой
def get_admin_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Режим обслуживания пользователя")]],  # Передаем кнопки в список
        resize_keyboard=True

    )
    return keyboard


async def send_admin_log(bot: Bot, message: str):
    # Получаем реплай-клавиатуру
    keyboard = get_admin_reply_keyboard()
    for admin_chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=admin_chat_id, text=message, reply_markup=keyboard)
        except Exception as e:
            # Логирование ошибки с деталями
            logging.error(
                f"Ошибка при отправке сообщения админу с ID {admin_chat_id}. "
                f"Сообщение: {message}. Ошибка: {e}"
            )
