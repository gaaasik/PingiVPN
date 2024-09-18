# bot/handlers/device_choice.py

from aiogram import Router, types
from aiogram.types import CallbackQuery

from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
from bot.keyboards.inline import download_app_keyboard
from models.user import User

router = Router()


# Обработчик для выбора устройства
@router.callback_query(lambda c: c.data.startswith("device_"))
async def handle_device_choice(callback_query: CallbackQuery):
    # Удаляем неважные сообщения
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)
    device = callback_query.data.split('_')[1]

    # Определяем ссылку для скачивания в зависимости от устройства
    if device == 'android':
        download_link = "https://play.google.com/store/apps/details?id=com.wireguard.android"
    elif device == 'iphone':
        download_link = "https://apps.apple.com/us/app/wireguard/id1441195209"
    elif device == 'mac':
        download_link = "https://www.wireguard.com/install/"
    elif device == 'linux':
        download_link = "https://www.wireguard.com/install/"
    elif device == 'windows':
        download_link = "https://www.wireguard.com/install/"

    # Отправляем сообщение с кнопками для скачивания приложения
    message = await callback_query.message.answer(
        "Скачайте *официальное* приложение *WireGuard* на ваше устройство.",
        reply_markup=download_app_keyboard(download_link),
        parse_mode="Markdown"
    )

    # Обновляем устройство пользователя в базе данных
    User.update_device(callback_query.from_user.id, device)
    print(f"Пользователь {callback_query.from_user.id} - @{callback_query.from_user.username} выбрал устройство: {device}")

    # Сохраняем сообщение как важное с типом 'device_choice'
    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                  message_type="device_choice")

    await callback_query.answer()
