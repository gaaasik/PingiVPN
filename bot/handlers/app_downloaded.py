# Это файл handlers/app_downloaded.py

from aiogram import Router, types
from aiogram.types import CallbackQuery
from bot.keyboards.inline import config_or_qr_keyboard
from bot.handlers.cleanup import store_message, delete_unimportant_messages, \
    store_important_message  # Используем функцию удаления сообщений
from models.UserCl import UserCl

router = Router()

# Обработчик для нажатия на кнопку "Я скачал ✅"
@router.callback_query(lambda c: c.data == "app_downloaded")
async def handle_app_downloaded(callback_query: CallbackQuery):

    # Удаляем неважные сообщения
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)



    us = await UserCl.load_user(callback_query.message.chat.id)
    check_protocol_vless = False
    url_vless = ""
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
        # Отправляем дальнейшую инструкцию с кнопками для скачивания конфигурации и QR-кода


        vpn_link = (
            "vless://90b5d83f-e3c6-4381-91c4-7d624dc1c490@194.87.208.18:443?"
            "type=tcp&security=reality&pbk=kX9Di-f2fMnJjRxx2rMsy6_Pe5gXyRO4S1NrZw8Dcyk&"
            "fp=chrome&sni=yahoo.com&sid=9c&spx=%2F&flow=xtls-rprx-vision#Vless-vless_5_Netherlands"
        )
        message = await callback_query.message.answer(
            f"Скопируйте ссылку ниже и вставьте в приложение VPN:\n\n`{vpn_link}`",
            parse_mode="Markdown",
        )




        # message = await callback_query.message.answer(
        #     f"Нажмите на ссылку, чтобы скопировать её в буфер обмена и вставьте в приложение:\n\n"
        #     f'{url_vless}',
        #     parse_mode="Markdown",
        # )
    except IndexError:
        print("Список серверов пуст или указан индекс вне диапазона.")
        return None  # Возвращаем None, если списка серверов нет или он пуст

    # Сохраняем важное сообщение с типом "app_downloaded"
    await store_important_message(
        callback_query.bot,
        callback_query.message.chat.id,
        message.message_id,
        message,
        message_type="app_downloaded"  # Маппим это сообщение как "app_downloaded"
    )
    # Исправленный вызов: теперь передаем объект bot
    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message)

    await callback_query.answer()




    # try:
    #     # Отправляем дальнейшую инструкцию с кнопками для скачивания конфигурации и QR-кода
    #     message = await callback_query.message.answer(
    #         f"Импортируйте конфигурационный файл в приложении \n\nИли отсканируйте QR-код через приложение. \n\n Для простоты понимания в подробной инструкции есть видео {url_vless}",
    #         reply_markup=config_or_qr_keyboard()
    #     )
    # except IndexError:
    #     print("Список серверов пуст или указан индекс вне диапазона.")
    #     return None  # Возвращаем None, если списка серверов нет или он пуст
    #
    # # Сохраняем важное сообщение с типом "app_downloaded"
    # await store_important_message(
    #     callback_query.bot,
    #     callback_query.message.chat.id,
    #     message.message_id,
    #     message,
    #     message_type="app_downloaded"  # Маппим это сообщение как "app_downloaded"
    # )
    # # Исправленный вызов: теперь передаем объект bot
    # await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message)
    #
    # await callback_query.answer()
