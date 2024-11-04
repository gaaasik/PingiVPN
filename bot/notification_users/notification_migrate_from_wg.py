
from aiogram import types, Bot, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging

from bot.keyboards.inline import main_menu_inline_keyboard
from bot.handlers.all_menu.main_menu import show_main_menu
from bot.keyboards.reply import reply_keyboard_main_menu

logger = logging.getLogger(__name__)
router = Router()
# Основное уведомление с reply-клавиатурой
async def send_initial_update_notification(chat_id: int, bot: Bot):
    """
    Отправляет первое уведомление об обновлении с reply-клавиатурой.
    """
    try:
        # Формируем текст для основного уведомления
        text = (
            "🚨 *У нас обновление!* 🚨\n\n"
            "Теперь доступен новый протокол *VLESS* с улучшенными характеристиками скорости и защиты.\n\n"
            "⚙️ *Высокая скорость*\n"
            "🛡️ *Защита и анонимность*\n"
            "📈 *Стабильность*\n"
            "📲 Переходите на новый протокол для максимального удобства и надежности!"
        )

        # Отправляем сообщение с reply-клавиатурой
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_keyboard_main_menu, parse_mode="Markdown")
        logger.info(f"Основное уведомление об обновлении отправлено пользователю {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке основного уведомления: {e}")


# Второе уведомление с inline-кнопками
async def send_choice_notification(chat_id: int, bot: Bot):
    """
    Отправляет второе уведомление с inline-кнопками для выбора действия.
    """
    try:
        # Текст уведомления с выбором действия
        choice_text = (
            f"🚨 Улучшения, которые вы ждали!\n\n"
            f"Мы полностью уходим от *WireGuard*, так как он работает нестабильно, и провайдеры активно блокируют подключение.\n\n"
            f"📲 Вам нужно добавить ключ *VLESS* и установить новое приложение для подключения. Вам будет доступен 🎁 *пробный период 7 дней*.\n\n"
        )

        # Создаем inline-кнопки
        choice_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")],
                [InlineKeyboardButton(text="⚠️ Остаться на WireGuard", callback_data="stay_on_wg")]
            ]
        )

        # Отправляем сообщение с inline-кнопками
        await bot.send_message(chat_id=chat_id, text=choice_text, reply_markup=choice_keyboard, parse_mode="Markdown")
        logger.info(f"Уведомление с выбором отправлено пользователю {chat_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления с выбором: {e}")
# Обработчик для inline-кнопок выбора
@router.callback_query(lambda c: c.data in ["connect_vpn", "stay_on_wg", "wg_working"])
async def handle_choice_callback(callback_query: types.CallbackQuery):
    bot = callback_query.bot
    chat_id = callback_query.message.chat.id

    if callback_query.data == "connect_vpn":
        # Пользователь выбрал VLESS
        await show_main_menu(chat_id, bot)
        await callback_query.answer("Вы перешли на VLESS 🚀", show_alert=True)

    elif callback_query.data == "stay_on_wg":
        # Пользователь решил остаться на WireGuard
        warning_text = (
            f"⚠️ Остаться на WireGuard не получится, провайдер активно блокирует подключения.\n\n"
            f"Зачем ждать проблем?\nС *VLESS* у вас будет гарантированная стабильность работы VPN."
        )

        # Создаем вторую inline-клавиатуру с двумя кнопками
        second_choice_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")],
                [InlineKeyboardButton(text="❓ У меня все работает", callback_data="wg_working")]
            ]
        )

        # Отправляем предупреждение и вторую inline-клавиатуру
        await bot.send_message(chat_id=chat_id, text=warning_text, reply_markup=second_choice_keyboard, parse_mode="Markdown")
        await callback_query.answer()

    elif callback_query.data == "wg_working":
        # Пользователь подтвердил, что WireGuard работает
        final_warning_text = (
            "⏳ *Скоро перестанет...*\nРекомендуем перейти на VLESS.\n"
            "Если вы уверены в WireGuard, напишите в поддержку."
        )

        final_choice_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Перейти на VLESS", callback_data="connect_vpn")]
            ]
        )

        # Отправляем окончательное предупреждение
        await bot.send_message(chat_id=chat_id, text=final_warning_text, reply_markup=final_choice_keyboard, parse_mode="Markdown")
        await callback_query.answer()