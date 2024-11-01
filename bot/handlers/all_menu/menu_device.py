# bot/handlers/menu_device.py

from aiogram import Router, types
from aiogram.types import CallbackQuery
from bot.handlers.all_menu.menu_subscriptoin_check import subscribe_keyboard
from bot.handlers.cleanup import delete_unimportant_messages, store_important_message
from bot.keyboards.inline import download_app_keyboard
from bot.utils.subscription_check import check_subscription_channel
from models.UserCl import UserCl

router = Router()


def get_instruction_text_for_device(device: str, vpn_link: str) -> str:
    # Общий текст инструкций, уникальный для каждого устройства
    if device.lower() == "android":
        instruction_text = (
            f"📱 <b>Инструкция для Android:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='https://play.google.com/store/apps/details?id=com.hiddify'><b>Hiddify</b> (Play Market)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Нажмите круглую кнопку для подключения — и наслаждайтесь быстрой связью! 🌐\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "iphone":
        instruction_text = (
            f"📱 <b>Инструкция для iPhone:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='https://apps.apple.com/us/app/streisand/id6450534064'><b>Streisand</b> (App Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "mac":
        instruction_text = (
            f"💻 <b>Инструкция для Mac:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='https://apps.apple.com/us/app/foxray/id6448898396'><b>Foxray</b> (App Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "linux":
        instruction_text = (
            f"🐧 <b>Инструкция для Linux:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='https://github.com/MatsuriDayo/nekoray/'><b>Nekoray</b> (GitHub)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "windows":
        instruction_text = (
            f"💻 <b>Инструкция для Windows:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='https://apps.microsoft.com/detail/9pdfnl3qv2s5?hl=ru-ru&gl=RU'><b>Hiddify</b> (Microsoft Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )
    else:
        instruction_text = "Пожалуйста, выберите устройство для получения инструкции."

    return instruction_text


# Обработчик для выбора устройства
@router.callback_query(lambda c: c.data.startswith("device_"))
async def handle_device_choice(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot
    us = await UserCl.load_user(chat_id)

    # Удаляем неважные сообщения
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)

    if not await us.check_subscription_channel():
        await callback_query.message.answer(
            f"VPN работает *без рекламы*. Чтобы начать пользоваться — *подпишитесь* на канал *Pingi Hub*",
            reply_markup=subscribe_keyboard(),
            parse_mode="Markdown"

        )
        await callback_query.answer()
        return

    device = callback_query.data.split('_')[1]
    await us.device.set(device)
    ################################################
    #НАДО ПОМЕНЯТЬ

    # Логика для проверки протокола VLESS
    check_protocol_vless = False
    for server in us.servers:
        if await server.name_protocol.get() == "vless":
            check_protocol_vless = True
            break

    # Если VLESS протокол найден, используем соответствующий URL
    if check_protocol_vless:
        for server in us.servers:
            if await server.name_protocol.get() == "vless":
                url_vless = await server.url_vless.get()
                break
    else:
        await us.add_key_vless()
        url_vless = await us.servers[0].url_vless.get()
    #############################################
    try:
        text = get_instruction_text_for_device(device, url_vless)
        message = await callback_query.message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=download_app_keyboard(device)  # Передаём `device` в `download_app_keyboard`
        )
        await callback_query.answer()

    except IndexError:
        print("Список серверов пуст или указан индекс вне диапазона.")
        return None  # Возвращаем None, если списка серверов нет или он пуст

    # Сохраняем сообщение как важное с типом 'device_choice'
    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                  message_type="device_choice")

    await callback_query.answer()
