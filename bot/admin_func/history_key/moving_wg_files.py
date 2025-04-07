import logging
import os
import re
import shutil
import qrcode
from models.ServerCl import ServerCl



async def move_in_history_files_wg(old_key: ServerCl, server_ip: str=None, user_ip: str=None, condition: str=None):
    """
    Перемещает файлы PingiVPN.conf и PingiVPN.png в папку history_key
    внутри директории пользователя, полученной из .env.
    Перед перемещением проверяет соответствие server_ip и user_ip в файле конфигурации.

    :param old_key: объект ServerCl, содержащий chat_id пользователя.
    :param server_ip: (опционально) IP сервера, если не передан - берется из old_key.
    :param user_ip: (опционально) IP пользователя, если не передан - берется из old_key.
    """
    try:
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

        # Проверяем, пуста ли папка пользователя
        if not os.listdir(user_folder):
            logging.warning(f"Папка пользователя {user_folder} пустая. Нет файлов для перемещения.")
            return

        # Проверяем, существует ли папка history_key, создаем если нет
        history_folder = os.path.join(user_folder, "history_key")
        os.makedirs(history_folder, exist_ok=True)

        # Путь к файлу конфигурации
        conf_file = os.path.join(user_folder, "PingiVPN.conf")

        if condition == "all":
            with open(conf_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Найти IP пользователя
            user_ip_match = re.search(r'Address\s*=\s*([\d.]+)/', content)
            user_ip_formatted = user_ip_match.group(1).replace(".", "_") if user_ip_match else None
            # Найти IP сервера
            server_ip_match = re.search(r'Endpoint\s*=\s*([\d.]+):', content)
            server_ip_formatted = server_ip_match.group(1).replace(".", "_") if server_ip_match else None

        else:
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
            return False

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
            return False

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
                return False

            file_server_ip = endpoint_match.group(1)
            file_user_ip = address_match.group(1)

            # Проверяем соответствие IP-адресов
            if file_server_ip == server_ip and file_user_ip == user_ip:
                logging.info(f"Файлы пользователя {chat_id} уже актуальны. Действия не требуются.")
                return False
            else:
                logging.warning(f"⚠Несоответствие IP в файле {conf_file}. Архивируем файлы...")
                await move_in_history_files_wg(new_key, file_server_ip, file_user_ip)

        # Ищем папку history_key
        history_folder = os.path.join(user_folder, "history_key")
        if not os.path.exists(history_folder):
            logging.error(f"Ошибка: Папка history_key у пользователя {chat_id} отсутствует.")
            return False

        # Ищем файлы с нужным именем в history_key
        history_conf_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.conf")
        history_png_file = os.path.join(history_folder, f"{server_ip_formatted}-{user_ip_formatted}.png")

        if not os.path.exists(history_conf_file) or not os.path.exists(history_png_file):
            logging.error(f"Ошибка: Не найдены актуальные файлы в history_key у {chat_id}.")
            return False

        # Восстанавливаем файлы из history_key
        shutil.copy(history_conf_file, os.path.join(user_folder, "PingiVPN.conf"))
        shutil.copy(history_png_file, os.path.join(user_folder, "PingiVPN.png"))

        logging.info(f"Успешно восстановлены актуальные файлы для пользователя {chat_id}")

        # Удаляем старые файлы из history_key
        os.remove(history_conf_file)
        os.remove(history_png_file)

        logging.info(f"🗑Удалены старые файлы {history_conf_file} и {history_png_file} из history_key.")
        return True

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
            logging.info(f"Файл {conf_file} прошел проверку: server_ip и user_ip совпадают.")
            return True
        else:
            logging.error(
                f"Несоответствие данных в {conf_file}\n"
                f" Ожидалось: server_ip={server_ip}, user_ip={user_ip}\n"
                f" В файле:  server_ip={file_server_ip}, user_ip={file_user_ip}"
            )
            return False

    except Exception as e:
        logging.error(f"🔥 Ошибка при проверке конфигурационного файла {conf_file}: {e}")
        return False


async def generate_qr_code(input_file, output_file):
    """Генерирует QR-код из конфигурационного файла WireGuard."""
    try:
        with open(input_file, 'r', encoding="utf-8") as file:
            config_data = file.read()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config_data)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        img.save(output_file)

        logging.info(f"QR-код успешно сохранен: {output_file}")
    except Exception as e:
        logging.error(f"Ошибка при создании QR-кода: {e}")





