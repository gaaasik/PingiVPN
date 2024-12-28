# bot/handlers/menu_device.py
import logging

from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from bot.handlers.all_menu.menu_subscriptoin_check import subscribe_keyboard
from bot.handlers.cleanup import delete_unimportant_messages, store_important_message
from bot.keyboards.inline import download_app_keyboard
from bot.utils.subscription_check import check_subscription_channel
from models.UserCl import UserCl

router = Router()
# Ссылки на приложения WireGuard для разных платформ
WIREGUARD_LINKS = {
    "android": "https://play.google.com/store/apps/details?id=com.wireguard.android",
    "iPhone": "https://apps.apple.com/us/app/wireguard/id1441195209",
    "windows": "https://download.wireguard.com/windows-client/",
    "mac": "https://apps.apple.com/us/app/wireguard/id1451685025",
    "linux": "https://www.wireguard.com/install/"
}

VLESS_LINKS = {
    "android": "https://play.google.com/store/apps/details?id=com.v2ray.ang",
    "iPhone": "https://apps.apple.com/ru/app/streisand/id6450534064",
    "windows": "https://apps.microsoft.com/detail/9pdfnl3qv2s5?hl=ru-ru&gl=RU",
    "mac": "https://apps.apple.com/us/app/foxray/id6448898396",
    "linux": "https://github.com/MatsuriDayo/nekoray/"
}


# Клавиатура для WireGuard
def wireguard_keyboard(device):
    buttons = []
    # Добавляем кнопку для загрузки приложения
    if device in WIREGUARD_LINKS:
        buttons.append([InlineKeyboardButton(text="📥 Скачать WireGuard", url=WIREGUARD_LINKS[device])])

    # Кнопка подтверждения "Я скачал ✅"
    buttons.append([InlineKeyboardButton(text="Я скачал ✅", callback_data="app_downloaded")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_instruction_text_for_device(device: str, vpn_link: str) -> str:
    # Получаем ссылку на приложение для устройства из VLESS_LINKS
    app_link = VLESS_LINKS.get(device.lower())

    # Общий текст инструкций, уникальный для каждого устройства
    if device.lower() == "android":
        instruction_text = (
            f"📱 <b>Инструкция для Android:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='{app_link}'><b>V2Ray</b> (Play Market)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Нажмите круглую кнопку для подключения — и наслаждайтесь быстрой связью! 🌐\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "iphone":
        instruction_text = (
            f"📱 <b>Инструкция для iPhone:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='{app_link}'><b>Streisand</b> (App Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "mac":
        instruction_text = (
            f"💻 <b>Инструкция для Mac:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='{app_link}'><b>Foxray</b> (App Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "linux":
        instruction_text = (
            f"🐧 <b>Инструкция для Linux:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='{app_link}'><b>Nekoray</b> (GitHub)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
            f"3️⃣ Подключитесь и наслаждайтесь стабильной работой! 🚀\n\n"
            f"<b>Ваш ключ:</b>\n<pre>{vpn_link}</pre>"
        )

    elif device.lower() == "windows":
        instruction_text = (
            f"💻 <b>Инструкция для Windows:</b>\n\n"
            f"1️⃣ Нажмите на ваш ключ <b>VLESS</b> (скопируйте его).\n"
            f"2️⃣ Откройте приложение <a href='{app_link}'><b>Hiddify</b> (Microsoft Store)</a> и выберите ➕ «Импорт из буфера обмена».\n\n"
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

    # Проверяем наличие серверов
    if not us.servers:
        # Если серверов нет, добавляем новый сервер VLESS
        if not await us.add_key_vless():
            await callback_query.message.answer(
                "🥲К сожалению, cейчас все сервера полностью заполенны. Сейчас мы добавляем места, повторите попытку подключения через 30 минут😉.",
                parse_mode="Markdown"
            )
            logging.error(f"Пользователь добавляется, а свободных ключей нету chat_id{chat_id}, {await us.user_name_full.get()}")
            return


    try:
        if us.active_server:
            ##########################################          VLESS          ######################################################
            if await us.active_server.name_protocol.get() == "vless":
                url_vless = await us.active_server.url_vless.get()
                text = get_instruction_text_for_device(device, url_vless)
                await callback_query.message.answer(
                    text,
                    parse_mode="HTML",  # ЭТО ОБЯЗАТЕЛЬНО ИНАЧЕ ОШИБКА
                    disable_web_page_preview=True,
                    reply_markup=download_app_keyboard(device)  # Передаём `device` в `download_app_keyboard`
                )
                await callback_query.answer()
                return


            #############################################       WIREGUARD     #######################################################
            if await us.active_server.name_protocol.get() == "wireguard":
                # Отправляем сообщение с ссылкой на приложение WireGuard
                await callback_query.message.answer(
                    "Скачайте официальное приложение WireGuard на ваше устройство.",
                    reply_markup=wireguard_keyboard(device),
                    parse_mode="Markdown"
                )
                await callback_query.answer()
                return
        else:
            logging.error(f"У пользователя есть ")


    except IndexError as e:
        logging.error(f"Ошибка при обработке устройства: {e}")
        await callback_query.message.answer("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")
        await callback_query.answer()







