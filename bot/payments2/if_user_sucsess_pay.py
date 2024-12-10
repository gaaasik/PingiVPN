import aiosqlite
from datetime import datetime
import logging
from aiogram import Bot
import os

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.admin import ADMIN_CHAT_IDS
from bot.handlers.all_menu.main_menu import show_main_menu
from bot.handlers.cleanup import message_types_mapping, delete_message_with_type, store_message



# Обработка действий после успешной оплаты
async def handle_post_payment_actions(bot: Bot, chat_id: int):
    """Выполняет действия после успешной оплаты."""

    # Удаление сообщений об оплате (здесь можно вставить свой код)
    # Например:
    await delete_message_with_type(chat_id, "msg_with_pay_url", bot)
    await delete_message_with_type(chat_id, "account_status", bot)

    # Отправка сообщения пользователю
    try:
        # Создание клавиатуры с кнопками
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Супер!", callback_data="super")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
        #await show_main_menu(chat_id,bot)
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 Спасибо за оплату! 🎉\n\n"
                "🙌 Ваш платеж успешно завершен, и ваша подписка *активна*. \n\n"
                "🌍 Мы ценим ваше доверие и рады, что вы выбрали *Pingi VPN* для безопасного доступа к интернету. \n\n"
                "🚀 Если у вас возникнут вопросы или проблемы, наша поддержка всегда готова помочь. \n\n"
                "👥 Делитесь с друзьями и получайте *бонусные дни*\n\n"
                "💫 *Приятного использования и стабильного соединения!* 🌐✨"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard
        )


        logging.info(f"Сообщение пользователю {chat_id} об успешной оплате отправлено.")

    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

    # Отправка уведомлений администраторам
    for admin_chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=f" 💸💸💸 Уведомление администратору: пользователь с ID {chat_id} успешно оплатил подписку."
            )
            logging.info(f"Уведомление об оплате отправлено администратору {admin_chat_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_chat_id}: {e}")

