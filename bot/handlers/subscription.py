from aiogram import Router, types
from aiogram.types import CallbackQuery
from bot.utils.subscription_check import check_subscription_channel
from bot.handlers.cleanup import store_important_message, delete_important_message
from bot.keyboards.inline import config_or_qr_keyboard, subscribe_keyboard

router = Router()


# Обработчик кнопки "Я подписался"
@router.callback_query(lambda c: c.data == "check_subscription")
async def handle_check_subscription(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot

    # Проверяем подписку через Telegram API
    if await check_subscription_channel(chat_id, bot):
        # Удаляем старое сообщение с кнопками
        await delete_important_message(chat_id, "subscription_check", bot)
    else:
        # Удаляем старое сообщение и отправляем новое с кнопками "Перейти на канал" и "Я подписался"
        await delete_important_message(chat_id, "subscription_check", bot)

        message = await callback_query.message.answer(
            "Вы ещё не подписались.\n\n"
            "🎯 *Оперативные решения* — мы быстро реагируем на блокировки и всегда находим обходные пути!\n\n"
            "💬 *Поддержка 24/7* — задавайте вопросы и получайте ответы прямо в канале.\n\n"
            "🚀 *Первым узнавайте о новинках* — улучшения сервиса и новые функции только для подписчиков!",
            parse_mode="Markdown",
            reply_markup=subscribe_keyboard()
        )
        await store_important_message(bot, chat_id, message.message_id, message, message_type="subscription_check")

    await callback_query.answer()
