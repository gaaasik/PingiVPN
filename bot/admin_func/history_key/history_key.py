import logging
import os
import shutil
from datetime import datetime
import re

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Chat, User, Message

from bot.admin_func.searh_user.search_user_handlers import handle_chat_id_input
from bot.admin_func.searh_user.utils import format_history_key
from bot.admin_func.states import AdminStates
from models.ServerCl import ServerCl
from models.UserCl import UserCl
from dotenv import load_dotenv

router = Router()
load_dotenv()

############Толян начал ебашить кнопки


@router.callback_query(lambda c: c.data.startswith("history_key_show_"))
async def handle_history_key_show(callback: CallbackQuery, state: FSMContext):
    """Выводит информацию о выбранном ключе из history_key_list."""
    logging.info("Зашли в history_key_show_")

    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        logging.error("Ошибка: current_user отсутствует в state.")
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    if not user.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.")
        return

    chat_id = user.chat_id
    us = await UserCl.load_user(chat_id)
    if not us or not us.history_key_list:
        await callback.message.edit_text("❌ История ключей пуста.")
        return

    # Получаем индекс выбранного ключа
    index = int(callback.data.split("_")[-1])
    selected_key = us.history_key_list[index]

    # Сохраняем индекс выбранного ключа в state
    await state.update_data(selected_history_index=index)

    # Формируем сообщение с помощью format_history_key
    key_info = await format_history_key(selected_key, index)
    keyboard = await generate_history_keyboard(us.history_key_list, index)

    await callback.message.edit_text(key_info, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


async def generate_history_keyboard(history_key_list, selected_index):
    """Создает клавиатуру с историей ключей."""
    buttons = []
    index = 0
    for i, key in enumerate(history_key_list):
        name = await key.name_server.get()
        if i == selected_index:
            index = i
            prefix = "📍 "
        else:
            prefix = ""

        buttons.append([InlineKeyboardButton(text=f"{prefix}{name}", callback_data=f"history_key_show_{i}")])
    buttons.append([InlineKeyboardButton(text="✅ Сделать ключ основным", callback_data=f"change_active_server_{index}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_back_menu")]) #search_by_chat_id
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "my_back_menu")
async def my_back_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    logging.info("Зашли в my_back_menu")

    data = await state.get_data()
    user = data.get("current_user")
    if not user:
        logging.error("Ошибка: current_user отсутствует в state.")
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    print("user.chat_id = ", user.chat_id)

    # Создаем фейковое сообщение
    fake_message = Message(
        message_id=callback.message.message_id,  # Берем ID текущего сообщения
        from_user=User(id=1388513042, is_bot=False, first_name="Admin"),  # Фейковый отправитель
        chat=Chat(id=callback.message.chat.id, type="private"),  # Используем ID текущего чата
        text=str(user.chat_id),  # Передаем chat_id как текст
        date=datetime.utcnow()  # Обязательное поле date
    )

    # Передаем fake_message вместо chat_id
    await handle_chat_id_input(fake_message, state)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("change_active_server_"))
async def handler_change_active_server(callback: CallbackQuery, state: FSMContext):
    """Возвращает в состояние ожидания ввода Chat ID."""
    logging.info("Запуск change_active_server_")
    data = await state.get_data()
    user = data.get("current_user")
    us = await UserCl.load_user(user.chat_id)
    index = int(callback.data.split("_")[-1])
    old_key = us.active_server
    new_key = us.history_key_list[index]
    del us.history_key_list[index]
    await new_key.date_key_off.set(await old_key.date_key_off.get())
    us.history_key_list.append(old_key)
    us.servers.remove(old_key)
    us.servers.append(new_key)
    await us.choosing_working_server()
    logging.info("Из history_key_list удален выбранный ключ и добавлен старый ключ")
    await us.push_field_json_in_db("history_key_list")
    await us.push_field_json_in_db("servers")
    logging.info("Обновил базу данных ")
    
    await new_key.enable.set(True)
    await old_key.enable.set(False)
    logging.info("Отключил old_key, включил new_key")

    # Если старый ключ wireguard, значит нужно его переместить в history_key
    if await old_key.name_protocol.get() == "wireguard":
        await move_in_history_files_wg(old_key)
    # Если новый ключ wireguard, значит нужно его вытащить из history_key
    if await new_key.name_protocol.get() == "wireguard":
        await move_in_user_files_wg(new_key)





    await callback.message.answer(f"Изменил основной ключ у пользователя с chat_id {user.chat_id}.")
    await state.set_state(AdminStates.waiting_for_bonus_days)
    fake_message = Message(
        message_id=callback.message.message_id,  # Берем ID текущего сообщения
        from_user=User(id=1388513042, is_bot=False, first_name="Admin"),  # Фейковый отправитель
        chat=Chat(id=callback.message.chat.id, type="private"),  # Используем ID текущего чата
        text=str(user.chat_id),  # Передаем chat_id как текст
        date=datetime.utcnow()  # Обязательное поле date
    )

    # Передаем fake_message вместо chat_id
    await handle_chat_id_input(fake_message, state)
    await callback.answer()


async def move_in_history_files_wg(old_key: ServerCl, server_ip: str = None, user_ip: str = None):
    """
    Перемещает файлы PingiVPN.conf и PingiVPN.png в папку history_key
    внутри директории пользователя, полученной из .env.
    Перед перемещением проверяет соответствие server_ip и user_ip в файле конфигурации.

    :param old_key: объект ServerCl, содержащий chat_id пользователя.
    :param server_ip: (опционально) IP сервера, если не передан - берется из old_key.
    :param user_ip: (опционально) IP пользователя, если не передан - берется из old_key.
    """
    try:
        logging.info("Запустилась функция _______move_in_history_files_wg_________")
        base_directory = os.getenv("REGISTERED_USERS_DIR")
        if not base_directory:
            logging.error("Ошибка: Переменная окружения REGISTERED_USERS_DIR не найдена!")
            return

        # Получаем данные из объекта old_key, если не переданы вручную
        chat_id = str(old_key.user.chat_id)
        user_login = str(await old_key.user.user_login.get())
        server_ip = server_ip if server_ip else str(await old_key.server_ip.get())
        user_ip = user_ip if user_ip else str(await old_key.user_ip.get())

        # Преобразуем IP-адреса (заменяем точки на подчеркивания)
        server_ip_formatted = server_ip.replace(".", "_")
        user_ip_formatted = user_ip.replace(".", "_")

        # Ищем папку пользователя, начинающуюся с chat_id
        user_folder = None
        for folder in os.listdir(base_directory):
            if folder.startswith(chat_id):
                user_folder = os.path.join(base_directory, folder)
                break

        if not user_folder:
            logging.warning(f"Папка пользователя с chat_id {chat_id} не найдена. Создаем...")
            user_folder = os.path.join(base_directory, f"{chat_id}_{user_login}")
            os.makedirs(user_folder, exist_ok=True)

        # Проверяем, существует ли папка history_key, создаем если нет
        history_folder = os.path.join(user_folder, "history_key")
        os.makedirs(history_folder, exist_ok=True)

        # Путь к файлу конфигурации
        conf_file = os.path.join(user_folder, "PingiVPN.conf")

        # Проверяем соответствие server_ip и user_ip в файле конфигурации
        if not await validate_conf_file(conf_file, server_ip, user_ip):
            return  # Если проверка не прошла, не выполняем перемещение

        # Формируем новые имена файлов
        new_conf_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.conf")
        new_png_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.png")

        # Перемещаем файлы
        if os.path.exists(conf_file):
            shutil.move(conf_file, new_conf_file)
            logging.info(f"Файл {conf_file} перемещен в {new_conf_file}")
        else:
            logging.warning(f"Файл {conf_file} не найден!")

        png_file = os.path.join(user_folder, "PingiVPN.png")
        if os.path.exists(png_file):
            shutil.move(png_file, new_png_file)
            logging.info(f"Файл {png_file} перемещен в {new_png_file}")
        else:
            logging.warning(f"Файл {png_file} не найден!")

    except Exception as e:
        logging.error(f"Ошибка при перемещении файлов для chat_id {chat_id}: {e}")


async def move_in_user_files_wg(new_key: ServerCl):
    """
    Проверяет файлы PingiVPN.conf и PingiVPN.png в основной папке пользователя.
    Если server_ip и user_ip не совпадают с данными в PingiVPN.conf, архивирует текущие файлы и
    восстанавливает последние актуальные из history_key.

    :param new_key: объект ServerCl, содержащий chat_id пользователя.
    """
    try:
        logging.info("Запустилась функция move_in_user_files_wg")

        # Получаем базовую директорию из .env
        base_directory = os.getenv("REGISTERED_USERS_DIR")
        if not base_directory:
            logging.error("Ошибка: Переменная окружения REGISTERED_USERS_DIR не найдена!")
            return

        # Получаем данные из объекта new_key
        chat_id = str(new_key.user.chat_id)
        user_login = str(await new_key.user.user_login.get())
        server_ip = str(await new_key.server_ip.get())
        user_ip = str(await new_key.user_ip.get())

        # Преобразуем IP-адреса (заменяем точки на подчеркивания)
        server_ip_formatted = server_ip.replace(".", "_")
        user_ip_formatted = user_ip.replace(".", "_")

        # Ищем папку пользователя, начинающуюся с chat_id
        user_folder = None
        for folder in os.listdir(base_directory):
            if folder.startswith(chat_id):
                user_folder = os.path.join(base_directory, folder)
                break

        if not user_folder:
            logging.warning(f"Папка пользователя с chat_id {chat_id} не найдена.")
            return

        # Проверяем существование файла конфигурации
        conf_file = os.path.join(user_folder, "PingiVPN.conf")
        png_file = os.path.join(user_folder, "PingiVPN.png")

        if os.path.exists(conf_file) and os.path.exists(png_file):
            logging.info(f"В папке есть файлы PingiVPN.conf и PingiVPN.png для {chat_id}. Проверяем соответствие.")

            # Проверяем соответствие server_ip и user_ip в файле конфигурации
            with open(conf_file, "r", encoding="utf-8") as file:
                conf_content = file.read()

            # Извлекаем данные из файла
            endpoint_match = re.search(r"Endpoint\s*=\s*([\d\.]+):\d+", conf_content)
            address_match = re.search(r"Address\s*=\s*([\d\.]+)", conf_content)

            if not endpoint_match or not address_match:
                logging.error(f"Ошибка: Не удалось извлечь Endpoint или Address из {conf_file}")
                return

            file_server_ip = endpoint_match.group(1)
            file_user_ip = address_match.group(1)

            # Проверяем соответствие IP-адресов
            if file_server_ip == server_ip and file_user_ip == user_ip:
                logging.info(f"Файлы пользователя {chat_id} уже актуальны. Действия не требуются.")
                return
            else:
                logging.warning(f"⚠Несоответствие IP в файле {conf_file}. Архивируем файлы...")
                await move_in_history_files_wg(new_key, file_server_ip, file_user_ip)

        # Ищем папку history_key
        history_folder = os.path.join(user_folder, "history_key")
        if not os.path.exists(history_folder):
            logging.error(f"Ошибка: Папка history_key у пользователя {chat_id} отсутствует.")
            return

        # Ищем файлы с нужным именем в history_key
        history_conf_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.conf")
        history_png_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.png")

        if not os.path.exists(history_conf_file) or not os.path.exists(history_png_file):
            logging.error(f"Ошибка: Не найдены актуальные файлы в history_key у {chat_id}.")
            return

        # Восстанавливаем файлы из history_key
        shutil.copy(history_conf_file, os.path.join(user_folder, "PingiVPN.conf"))
        shutil.copy(history_png_file, os.path.join(user_folder, "PingiVPN.png"))

        logging.info(f"Успешно восстановлены актуальные файлы для пользователя {chat_id}")

        # Удаляем старые файлы из history_key
        os.remove(history_conf_file)
        os.remove(history_png_file)

        logging.info(f"🗑Удалены старые файлы {history_conf_file} и {history_png_file} из history_key.")

    except Exception as e:
        logging.error(f"Ошибка при валидации и восстановлении файлов для chat_id {chat_id}: {e}")


async def validate_conf_file(conf_file: str, server_ip: str, user_ip: str) -> bool:
    """
    Проверяет соответствие server_ip и user_ip в файле конфигурации

    :param conf_file: Путь к файлу PingiVPN.conf.
    :param server_ip: Ожидаемый server_ip.
    :param user_ip: Ожидаемый user_ip.
    :return: True если данные соответствуют, иначе False.
    """
    if not os.path.exists(conf_file):
        logging.error(f"❌ Файл конфигурации {conf_file} не найден.")
        return False

    try:
        with open(conf_file, "r", encoding="utf-8") as file:
            conf_content = file.read()

        # Извлекаем Endpoint (server_ip) и Address (user_ip)
        endpoint_match = re.search(r"Endpoint\s*=\s*([\d\.]+):\d+", conf_content)
        address_match = re.search(r"Address\s*=\s*([\d\.]+)", conf_content)

        if not endpoint_match or not address_match:
            logging.error(f"⚠️ Ошибка: Не удалось извлечь Endpoint или Address из {conf_file}")
            return False

        file_server_ip = endpoint_match.group(1)  # IP-адрес сервера
        file_user_ip = address_match.group(1)  # IP-адрес пользователя

        # Проверяем соответствие IP-адресов
        if file_server_ip == server_ip and file_user_ip == user_ip:
            logging.info(f"✅ Файл {conf_file} прошел проверку: server_ip и user_ip совпадают.")
            return True
        else:
            logging.error(
                f"⚠️ Несоответствие данных в {conf_file}\n"
                f"  🔹 Ожидалось: server_ip={server_ip}, user_ip={user_ip}\n"
                f"  🔹 В файле:  server_ip={file_server_ip}, user_ip={file_user_ip}"
            )
            return False

    except Exception as e:
        logging.error(f"🔥 Ошибка при проверке конфигурационного файла {conf_file}: {e}")
        return False