# bot/handlers/device_choice.py

from aiogram import Router, types
from aiogram.types import CallbackQuery

from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
from bot.keyboards.inline import download_app_keyboard
from models.UserCl import UserCl

router = Router()


# Обработчик для выбора устройства
@router.callback_query(lambda c: c.data.startswith("device_"))
async def handle_device_choice(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
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

    # Отправляем сообщение с кнопками для скачивания приложения
    message = await callback_query.message.answer(
        f"Скачайте *официальное* приложение *для vless протокола* на ваше устройство.",
        reply_markup=download_app_keyboard(download_link),
        parse_mode="Markdown"
    )

    # Обновляем устройство пользователя в базе данных
    us = await UserCl.load_user(chat_id)
    await us.device.set(device)
    print(f"Пользователь {callback_query.from_user.id} - @{callback_query.from_user.username} выбрал устройство: {device}")

    # Сохраняем сообщение как важное с типом 'device_choice'
    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                  message_type="device_choice")

    await callback_query.answer()
