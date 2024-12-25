import logging
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.handlers.admin import send_admin_log

# Инициализация роутера
router = Router()

@router.callback_query(lambda c: c.data == "thank_you")
async def handle_thank_you(callback_query: CallbackQuery):
    """
    Обработчик нажатия кнопки "Спасибо!".
    Отправляет ответ пользователю и уведомление администратору.
    """
    try:
        chat_id = callback_query.message.chat.id
        bot = callback_query.bot

        # Создаем клавиатуру с кнопкой "Главное меню"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])

        # Отвечаем пользователю с клавиатурой
        await callback_query.message.answer(
            "😊 Пожалуйста! Мы всегда рады помочь.",
            reply_markup=keyboard
        )

        # Уведомляем администраторов
        await send_admin_log(bot, f"Пользователь {chat_id} нажал кнопку 'Спасибо!'.")

        # Закрываем callback (убираем часы загрузки Telegram)
        await callback_query.answer()

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'Спасибо!': {e}")
