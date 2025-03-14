import logging
from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.UserCl import UserCl

router = Router()

# Клавиатура с кнопкой "Мне нужно настроить роутер Keenetic"
keenetic_warning_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Мне нужно настроить роутер Keenetic", callback_data="keenetic_start_setup")],
        [InlineKeyboardButton(text="✅ Подключить VLESS", callback_data="connect_vpn")]
    ]
)


@router.callback_query(lambda c: c.data == "keenetic_setup")
async def keenetic_warning(callback_query: CallbackQuery):
    """
    Показывает предупреждение о блокировке WireGuard.
    """
    try:
        warning_text = (
            "⚠️ <b>Важно знать перед настройкой!</b>\n\n"
            "🚨 <b>Некоторые интернет-провайдеры могут ограничивать или блокировать WireGuard.</b>\n"
            "🔹 Если это произойдет, мы <b>не сможем</b> гарантировать стабильную работу подключения.\n"
            "🔹 <b>Возврат средств не предусмотрен.</b> ❌\n\n"
            "💡 <b>Рекомендуем заранее проверить, поддерживает ли ваш провайдер WireGuard.</b>\n\n"
            "✅ Если вы понимаете риски и готовы продолжить настройку роутера Keenetic, нажмите кнопку ниже. ⬇️"
        )
        await callback_query.message.answer(warning_text, reply_markup=keenetic_warning_keyboard, parse_mode="HTML")
        await callback_query.answer()

    except Exception as e:
        logging.error(f"Ошибка в keenetic_warning: {e}")
        await callback_query.message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await callback_query.answer()


@router.callback_query(lambda c: c.data == "keenetic_start_setup")
async def keenetic_start_setup(callback_query: CallbackQuery):
    """
    Начинает процесс настройки роутера Keenetic.
    Проверяет наличие VLESS-ключа.
    Если у пользователя есть VLESS, он не может использовать WireGuard.
    """
    try:
        chat_id = callback_query.message.chat.id
        username = callback_query.from_user.username or None
        bot = callback_query.bot

        # Загружаем данные пользователя
        us = await UserCl.load_user(chat_id)

        # Проверяем, есть ли у пользователя уже VLESS-ключ
        if us.active_server and await us.active_server.name_protocol.get() == "vless":
            # Создаем клавиатуру с кнопкой "Помощь"
            warning_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
                ]
            )
            await callback_query.message.answer(
                "📂 <b>У вас уже есть VLESS-ключ.</b>\n\n"
                "❗ Запросите файл у поддержки.",
                parse_mode="HTML",
                reply_markup=warning_keyboard  # Добавляем клавиатуру с кнопкой "Помощь"
            )

            await callback_query.answer()
            return

        # Клавиатура с кнопками "Получить файл" Нет серверов для пользователя
        config_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📂 Получить файл", callback_data="get_config")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]

            ]
        )

        await callback_query.message.answer(
            "🎛️ <b>Настройка WireGuard на роутере Keenetic</b>\n\n"
            "⚠️ <b>Внимание!</b> Некоторые интернет-провайдеры активно блокируют WireGuard. "
            "Если ваш провайдер заблокирует подключение, мы не сможем это исправить, и возврат средств не предусмотрен. ❌\n\n"
            "🆓 При первой настройке вы получаете <b>7 дней бесплатного доступа</b>, затем подписка составит <b>199₽ в месяц</b>.\n\n"
            "📖 <b>Подробная инструкция по настройке:</b> <a href='https://dzen.ru/a/Z9RQT7xeJRfNa27u'>Открыть инструкцию</a>\n\n",
            reply_markup=config_keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        await callback_query.answer()

    except Exception as e:
        logging.error(f"Ошибка в keenetic_start_setup: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при настройке. Попробуйте позже.")
        await callback_query.answer()
