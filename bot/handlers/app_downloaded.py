# # Это файл handlers/app_downloaded.py
#
# from aiogram import Router, types
# from aiogram.types import CallbackQuery
# from bot.keyboards.inline import config_or_qr_keyboard, subscribe_keyboard
# from bot.handlers.cleanup import store_message, delete_unimportant_messages, \
#     store_important_message  # Используем функцию удаления сообщений
# from bot.utils.subscription_check import check_subscription_channel
# from models.UserCl import UserCl
# 
# router = Router()
#
#
#


# Обработчик для нажатия на кнопку "Я скачал ✅"
# @router.callback_query(lambda c: c.data == "app_downloaded")
# async def handle_app_downloaded(callback_query: CallbackQuery):
#     chat_id=callback_query.message.chat.id
#     bot = callback_query.bot
#     # # Удаляем неважные сообщения
#     #await delete_unimportant_messages(chat_id, bot)
#
#
#
#     us = await UserCl.load_user(callback_query.message.chat.id)
#     check_protocol_vless = False
#     url_vless = ""
#     for server in us.servers:
#         if await server.name_protocol.get() == "vless":
#             check_protocol_vless = True
#         else:
#             check_protocol_vless = False
#
#     if check_protocol_vless:
#         for server in us.servers:
#             if await server.name_protocol.get() == "vless":
#                 url_vless = await server.url_vless.get()
#     else:
#         await us.add_key_vless()
#         url_vless = await us.servers[0].url_vless.get()
#
#
#     try:
#
#         # Проверяем подписку пользователя
#         if not await check_subscription_channel(chat_id, bot):
#             # Отправляем сообщение с кнопками "Перейти на канал" и "Я подписался"
#             message = await callback_query.message.answer(
#                 "VPN работает без рекламы. Чтобы начать пользоваться — подпишитесь на канал Pingi Hub",
#                 reply_markup=subscribe_keyboard()
#             )
#             # Сохраняем это сообщение как важное
#             #await store_important_message(bot, chat_id, message.message_id, message,
#             #                              "subscription_check")
#             await callback_query.answer()
#             return
#         device = await us.device.get()
#         text = get_instruction_text_for_device(device)
#         print(device)
#         vpn_link = (
#             "vless://90b5d83f-e3c6-4381-91c4-7d624dc1c490@194.87.208.18:443?"
#             "type=tcp&security=reality&pbk=kX9Di-f2fMnJjRxx2rMsy6_Pe5gXyRO4S1NrZw8Dcyk&"
#             "fp=chrome&sni=yahoo.com&sid=9c&spx=%2F&flow=xtls-rprx-vision#Vless-vless_5_Netherlands"
#         )
#         message = await callback_query.message.answer(
#             f"{text}\n\n```\n{vpn_link}\n```",
#             parse_mode="Markdown",
#             disable_web_page_preview=True
#         )
#
#     except IndexError:
#         print("Список серверов пуст или указан индекс вне диапазона.")
#         return None  # Возвращаем None, если списка серверов нет или он пуст
#
#     await callback_query.answer()
#
#


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
