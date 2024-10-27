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
    print(f"cout_key  ДО начала добавления: {await us.count_key.get()}________________________________________")
    await us.add_key_vless()
    print(f"cout_key после добавления: {await us.count_key.get()}________________________________________")
    url_vless = await us.servers[0].url_vless.get()



    try:
        # Отправляем дальнейшую инструкцию с кнопками для скачивания конфигурации и QR-кода
        message = await callback_query.message.answer(
            f"Импортируйте конфигурационный файл в приложении \n\nИли отсканируйте QR-код через приложение. \n\n Для простоты понимания в подробной инструкции есть видео {url_vless}/n coutn_key{await us.count_key.get()}",
            reply_markup=config_or_qr_keyboard()
        )
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
