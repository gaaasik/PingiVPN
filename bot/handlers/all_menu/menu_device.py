# bot/handlers/menu_device.py

from aiogram import Router, types
from aiogram.types import CallbackQuery


from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
from bot.keyboards.inline import download_app_keyboard, subscribe_keyboard
from bot.utils.subscription_check import check_subscription_channel
from models.UserCl import UserCl

router = Router()

def get_instruction_text_for_device(device: str) -> str:
    # Общий текст инструкций, уникальный для каждого устройства
    if device.lower() == "android":
        instruction_text = (
            "Инструкция для Android:\n\n"
            "1) Нажмите на ваш ключ VLESS (скопируйте)\n"
            "2) Откройте приложение [Hiddify (Play Market)]("
            "https://play.google.com/store/apps/details?id=com.hiddify)  и выберите ➕ «Импорт из буфера обмена».\n\n"
            "3) Нажмите круглую кнопку для подключения — и наслаждайтесь быстрой связью!"
            "\n *Ваш ключ:*"
        )

    elif device.lower() == "iphone":
        instruction_text = (
            "Инструкция для iPhone:\n\n"
            "1) Нажмите на ваш ключ VLESS (скопируйте)\n"
            "2) Откройте приложение: [Streisand (App Store)](https://apps.apple.com/us/app/streisand/id6450534064) и "
            "выберите ➕ «Импорт из буфера обмена».\n\n"
            "3) Подключитесь и наслаждайтесь стабильной работой!"
            "\n *Ваш ключ:*"
        )

    elif device.lower() == "mac":
        instruction_text = (
            "Инструкция для Mac:\n\n"
            "1) Нажмите на ваш ключ VLESS (скопируйте)\n"
            "2) Откройте приложение: [Foxray (App Store)](https://apps.apple.com/us/app/foxray/id6448898396) и "
            "выберите ➕ «Импорт из буфера обмена».\n\n"
            "3) Подключитесь и наслаждайтесь стабильной работой!"
            "\n *Ваш ключ:*"
        )

    elif device.lower() == "linux":
        instruction_text = (
            "Инструкция для Linux:\n\n"
            "1) Нажмите на ваш ключ VLESS (скопируйте)\n"
            "2) Откройте приложение: [Nekoray](https://github.com/MatsuriDayo/nekoray/) и выберите ➕ «Импорт из "
            "буфера обмена».\n\n"
            "3) Подключитесь и наслаждайтесь стабильной работой!"
            "\n *Ваш ключ:*"

        )

    elif device.lower() == "windows":
        instruction_text = (
            "Инструкция для Windows:\n\n"
            "1) Нажмите на ваш ключ VLESS (скопируйте)\n"
            "2) Откройте приложение: [Hiddify](https://apps.microsoft.com/detail/9pdfnl3qv2s5?hl=ru-ru&gl=RU) и выберите ➕ «Импорт из буфера обмена».\n\n"
            "3) Подключитесь и наслаждайтесь стабильной работой!"
            "\n *Ваш ключ:*"
        )

    else:
        instruction_text = "Пожалуйста, выберите устройство для получения инструкции."

    return instruction_text

# Обработчик для выбора устройства
@router.callback_query(lambda c: c.data.startswith("device_"))
async def handle_device_choice(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot=callback_query.bot
    # Удаляем неважные сообщения
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)
    device = callback_query.data.split('_')[1]

    # # Определяем ссылку для скачивания в зависимости от устройства
    # if device == 'android':
    #     download_link = "https://play.google.com/store/apps/details?id=com.wireguard.android"
    # elif device == 'iphone':
    #     download_link = "https://apps.apple.com/us/app/wireguard/id1441195209"
    # elif device == 'mac':
    #     download_link = "https://www.wireguard.com/install/"
    # elif device == 'linux':
    #     download_link = "https://www.wireguard.com/install/"
    # elif device == 'windows':
    #     download_link = "https://www.wireguard.com/install/"

    # Определяем ссылку для скачивания в зависимости от устройства
    if device == 'android':
        download_link = "https://play.google.com/store/apps/details?id=com.v2ray.ang"
    elif device == 'iPhone':
        download_link = "https://apps.apple.com/us/app/streisand/id6450534064"
    elif device == 'mac':
        download_link = "https://apps.apple.com/us/app/foxray/id6448898396"
    elif device == 'linux':
        download_link = "https://github.com/MatsuriDayo/nekoray/"
    elif device == 'windows':
        download_link = "https://apps.microsoft.com/detail/9pdfnl3qv2s5?hl=ru-ru&gl=RU"


    #Промежуточное меню

    # # Отправляем сообщение с кнопками для скачивания приложения
    # message = await callback_query.message.answer(
    #     f"Установите официальное приложение для <b><a href='{download_link}'>{device}</a></b>\n\n<b><a href='{download_link}'>Скачать</a></b>\n \nИ <b>возвращайтесь</b> в бота, чтобы закончить настройку\n\n",
    #     reply_markup=download_app_keyboard(download_link),
    #     parse_mode="HTML",
    #     disable_web_page_preview=True  # Отключает предпросмотр ссылки
    # )

    # Обновляем устройство пользователя в базе данных

    us = await UserCl.load_user(chat_id)
    await us.device.set(device)
    print(f"Пользователь {callback_query.from_user.id} - @{callback_query.from_user.username} выбрал устройство: {device}")

    check_protocol_vless = False

    for server in us.servers:
        if await server.name_protocol.get() == "vless":
            check_protocol_vless = True
        else:
            check_protocol_vless = False

    if check_protocol_vless:
        for server in us.servers:
            if await server.name_protocol.get() == "vless":
                url_vless = await server.url_vless.get()
    else:
        await us.add_key_vless()
        url_vless = await us.servers[0].url_vless.get()


    try:

        # Проверяем подписку пользователя
        if not await check_subscription_channel(chat_id, bot):
            # Отправляем сообщение с кнопками "Перейти на канал" и "Я подписался"
            message = await callback_query.message.answer(
                "VPN работает без рекламы. Чтобы начать пользоваться — подпишитесь на канал Pingi Hub",
                reply_markup=subscribe_keyboard()
            )
            # Сохраняем это сообщение как важное
            #await store_important_message(bot, chat_id, message.message_id, message,
            #                              "subscription_check")
            await callback_query.answer()
            return
        device = await us.device.get()
        text = get_instruction_text_for_device(device)
        print(device)
        vpn_link = (
            "vless://90b5d83f-e3c6-4381-91c4-7d624dc1c490@194.87.208.18:443?"
            "type=tcp&security=reality&pbk=kX9Di-f2fMnJjRxx2rMsy6_Pe5gXyRO4S1NrZw8Dcyk&"
            "fp=chrome&sni=yahoo.com&sid=9c&spx=%2F&flow=xtls-rprx-vision#Vless-vless_5_Netherlands"
        )
        message = await callback_query.message.answer(
            f"{text}\n```\n{vpn_link}\n```",
            parse_mode="Markdown",
            disable_web_page_preview=True, reply_markup=download_app_keyboard(download_link)
        )


    except IndexError:
        print("Список серверов пуст или указан индекс вне диапазона.")
        return None  # Возвращаем None, если списка серверов нет или он пуст

    await callback_query.answer()


    # Сохраняем сообщение как важное с типом 'device_choice'
    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                  message_type="device_choice")

    await callback_query.answer()
