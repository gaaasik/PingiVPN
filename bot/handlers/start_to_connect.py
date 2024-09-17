# bot/handlers/show_qr.py
from aiogram import Router, types
from aiogram.filters import Command

from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
from bot.keyboards.inline import device_choice_keyboard
from bot.utils.file_manager import process_user_files, check_existing_user_files, send_files_to_user
import os

router = Router()


# Обработчик для кнопки "Подключиться 🚀"
@router.message(lambda message: message.text == "Подключиться 🚀")
async def handle_connect(message: types.Message):
    # Текст приветственного сообщения
    welcome_text = "Выберите устройство для настройки VPN."

    # Отправляем сообщение с клавиатурой выбора устройства
    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard())

    # Сохраняем сообщение как важное
    await store_important_message(message.bot, message.chat.id, sent_message.message_id, sent_message)




# @router.message(Command("show"))
# @router.message(lambda message: message.text == "Показать QR и файл")
# async def cmd_show_qr_and_file(message: types.Message):
#     # Сохраняем сообщение в базе данных
#     await store_message(message.chat.id, message.message_id, message.text, 'user')
#
#     # Получаем ID чата и никнейм пользователя
#     chat_id = message.chat.id
#     username = message.from_user.username or "unknown"
#
#     # Формируем название папки как "id чата_никнейм пользователя"
#     folder_name = f"{chat_id}_{username}"
#
#     # Отправка файлов пользователю
#     await send_files_to_user(message, folder_name, use_existing=False)





    # await store_message(message.chat.id, message.message_id, message.text, 'user')
    #
    # chat_id = message.chat.id
    # bot = message.bot
    #
    # # Получаем данные пользователя из базы данных
    # user_data = await get_user_by_telegram_id(message.from_user.id)
    #
    # if user_data:  # Проверяем, что данные пользователя и номер телефона существуют
    #     nickname = user_data[3] if user_data[3] else "unknown"  # Никнейм пользователя или "unknown", если никнейм отсутствует
    #     folder_name = f"{chat_id}_{nickname}"  # Формируем имя папки
    #
    #     try:
    #         # **Добавляем проверку и создание папки пользователя**
    #         if not check_existing_user_files(chat_id):
    #             # Если папка не существует или в ней нет нужных файлов, создаем их
    #             await send_files_to_user(message, folder_name, use_existing=False)
    #
    #         # Используем обновленную функцию, чтобы получить файлы для пользователя
    #         config_file, qr_code_file = await process_user_files(folder_name)
    #
    #         # Отправляем QR-код
    #         sent_qr_code = await message.answer_photo(photo=qr_code_file)
    #         await store_important_message(sent_qr_code.chat.id, sent_qr_code.message_id)
    #
    #         # Отправляем конфигурационный файл
    #         sent_config_file = await message.answer_document(document=config_file)
    #         await store_important_message(sent_config_file.chat.id, sent_config_file.message_id)
    #
    #         # Отправляем инструкцию с инлайн-кнопкой
    #         sent_instruction = await message.answer(
    #             f"👋 Всем привет! Успех на нашей стороне!\n\n{instructions_message}",
    #             parse_mode="Markdown",
    #             disable_web_page_preview=True,
    #             reply_markup=inline_kb
    #         )
    #         await store_important_message(sent_instruction.chat.id, sent_instruction.message_id)
    #
    #     except Exception as e:
    #         error_message = await message.answer(f"Ошибка: {str(e)}")
    #         await store_message(error_message.chat.id, error_message.message_id, error_message.text, 'bot')
    #
    #     # Удаляем старые текстовые сообщения, если это не важные сообщения
    #     await delete_unimportant_messages(chat_id, bot)
    #
    # else:
    #     # Сообщение, если пользователь не найден в системе
    #     error_message = await message.answer("Вы не найдены в системе. Пожалуйста, зарегистрируйтесь, нажав /start.")
    #     await store_message(error_message.chat.id, error_message.message_id, error_message.text, 'bot')