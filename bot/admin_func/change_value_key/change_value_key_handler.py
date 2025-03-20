import logging
import os
from datetime import datetime

from aiogram import Router, types, F
from aiogram.types import CallbackQuery, Message, Document, Chat, User
from aiogram.fsm.context import FSMContext

from bot.admin_func.history_key.history_key import handler_my_back_menu
from bot.admin_func.history_key.moving_wg_files import move_in_history_files_wg, validate_conf_file
from bot.admin_func.history_key.moving_wg_files import move_in_history_files_wg, validate_conf_file, generate_qr_code
from bot.admin_func.keyboards import get_key_change_keyboard
from bot.admin_func.searh_user.search_user_handlers import handle_chat_id_input
from bot.admin_func.states import AdminStates
import re

from models.UserCl import UserCl

router = Router()

# Регулярное выражение для проверки VLESS ключа
VLESS_PATTERN = re.compile(r'vless://[a-f0-9\-]+@[0-9\.]+:\d+\?.*')


@router.callback_query(F.data == "change_to_vless")
async def change_to_vless(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на VLESS'. Запрашивает новый ключ."""
    await callback.message.edit_text("✏️ Введите новый VLESS ключ:")
    await state.set_state(AdminStates.waiting_for_vless_key)
    await callback.answer()


@router.callback_query(F.data == "change_to_wireguard")
async def change_to_wireguard(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить ключ на WireGuard'. Запрашивает файл конфигурации."""
    await callback.message.edit_text("📁 Отправьте новый файл WireGuard:")
    await state.set_state(AdminStates.waiting_for_wireguard_file)
    await callback.answer()


@router.message(AdminStates.waiting_for_vless_key)
async def process_vless_key(message: Message, state: FSMContext):
    """Обработчик ввода нового VLESS ключа."""
    data = await state.get_data()
    us: UserCl = data.get("current_user")

    key = message.text.strip()

    if not VLESS_PATTERN.match(key):
        await message.answer("❌ Неверный формат VLESS ключа. Пожалуйста, введите корректный ключ.")
        return

    if us.active_server:
        # Вызов функции обновления ключа
        if await us.active_server.name_protocol.get() == "wireguard":
            logging.info("Перевел старые файлы в history_key")
            await move_in_history_files_wg(us.active_server)
    await us.update_key_to_vless(key)
    await message.answer("✅ Новый VLESS ключ сохранен.")
    # Вместо вызова handler_my_back_menu вызываем команду с inline-кнопки
    #await router.feed_callback_query(callback=CallbackQuery(id="123", from_user=message.from_user, data="my_back_menu"))

    fake_message = Message(
        message_id=message.message_id,  # Берем ID текущего сообщения
        from_user=User(id=message.message_id, is_bot=False, first_name="Admin"),  # Фейковый отправитель
        chat=Chat(id=message.chat.id, type="private"),  # Используем ID текущего чата
        text=str(us.chat_id),  # Передаем chat_id как текст
        date=datetime.utcnow()  # Обязательное поле date
    )

    # Передаем fake_message вместо chat_id
    await handle_chat_id_input(fake_message, state)
    await state.clear()


@router.message(AdminStates.waiting_for_wireguard_file, F.document)
async def process_wireguard_file(message: Message, state: FSMContext):

    """ Обрабатывает загруженный конфигурационный файл WireGuard  update_key_to_wireguard.
    - Проверяет формат файла (.conf).
    - Извлекает server_ip и user_ip.
    - Сохраняет файл в папку пользователя (создает, если нет).
    - Вызывает update_key_to_wireguard для обновления ключа."""

    try:
        logging.info("📥 Получен файл конфигурации WireGuard")

        data = await state.get_data()
        us: UserCl = data.get("current_user")
        user_login = str(await us.user_login.get())

        if not us:
            await message.answer("❌ Ошибка: Не удалось определить пользователя.")
            logging.error("❌ Ошибка: current_user отсутствует в состоянии.")
            return

        document: Document = message.document

        if not document.file_name.endswith(".conf"):
            await message.answer("❌ Ошибка: загруженный файл должен быть в формате .conf")
            logging.warning(f"⚠️ Файл {document.file_name} имеет неподдерживаемый формат.")
            return

        # Получаем путь к основной папке пользователей из .env
        base_directory = os.getenv("REGISTERED_USERS_DIR")
        if not base_directory:
            logging.error("❌ Ошибка: Переменная окружения base_directory_user_files_wg не найдена!")
            return

        # Определяем папку пользователя (ищем или создаем)
        chat_id = str(us.chat_id)
        user_folder = None

        for folder in os.listdir(base_directory):
            if folder.startswith(chat_id):
                user_folder = os.path.join(base_directory, folder)
                break



        if not user_folder:
            user_folder = os.path.join(base_directory, f"{chat_id}_{user_login}")
            os.makedirs(user_folder, exist_ok=True)
            logging.info(f"📂 Создана папка для пользователя: {user_folder}")

        if await us.active_server.name_protocol.get() == "wireguard":
            await move_in_history_files_wg(us.active_server)


        # Путь для сохранения нового конфигурационного файла
        file_path = os.path.join(user_folder, "PingiVPN.conf")

        # Скачивание файла
        file = await message.bot.get_file(document.file_id)
        await message.bot.download_file(file.file_path, file_path)

        logging.info(f"✅ Файл сохранен: {file_path}")

        # Читаем файл и извлекаем данные
        server_ip, user_ip = None, None
        with open(file_path, "r", encoding="utf-8") as conf_file:
            conf_content = conf_file.read()

            # Извлекаем server_ip (из строки Endpoint)
            endpoint_match = re.search(r"Endpoint\s*=\s*([\d\.]+):\d+", conf_content)
            if endpoint_match:
                server_ip = endpoint_match.group(1)

            # Извлекаем user_ip (из строки Address)
            address_match = re.search(r"Address\s*=\s*([\d\.]+)", conf_content)
            if address_match:
                user_ip = address_match.group(1)

        if not server_ip or not user_ip:
            await message.answer("❌ Ошибка: Не удалось извлечь server_ip или user_ip из файла.")
            logging.error(f"❌ Ошибка парсинга IP в файле {file_path}")
            return

        logging.info(f"🔍 Извлечены данные: server_ip={server_ip}, user_ip={user_ip}")

        # Обновляем ключ пользователя
        json_with_wg = {
            "server_ip": server_ip,
            "user_ip": user_ip
        }
        await us.update_key_to_wireguard(json_with_wg)

        # ✅ **Генерация QR-кода и сохранение**
        conf_file_path = os.path.join(user_folder, "PingiVPN.conf")
        qr_code_path = os.path.join(user_folder, "PingiVPN.png")
        generate_qr_code(conf_file_path, qr_code_path)
        logging.info(f"✅ QR-код создан: {qr_code_path}")

        await message.answer("✅ WireGuard-ключ успешно обновлен!")
        logging.info(f"✅ Ключ WireGuard успешно обновлен для пользователя {us.chat_id}")

    except Exception as e:
        logging.error(f"🔥 Ошибка в process_wireguard_file: {e}")
        await message.answer("❌ Произошла ошибка при обработке файла WireGuard.")
