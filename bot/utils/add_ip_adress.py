import os
import re

import aiosqlite


# Функция для извлечения IP-адресов из файла .conf
def extract_ips_from_conf(file_path):
    private_ip = None
    server_ip = None

    with open(file_path, 'r') as file:
        for line in file:
            # Ищем строку с адресом пользователя
            if 'Address =' in line:
                private_ip = re.search(r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}', line).group()

            # Ищем строку с адресом сервера
            if 'Endpoint =' in line:
                server_ip = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line).group()

    return private_ip, server_ip


# Функция для сканирования директории пользователей и обновления данных в базе данных
async def update_user_ip_info(bot, db_path, users_dir):
    async with aiosqlite.connect(db_path) as db:
        for folder in os.listdir(users_dir):
            # Проверяем, что папка начинается с числа (это chat_id)
            if folder.split('_')[0].isdigit():
                chat_id = int(folder.split('_')[0])
                folder_path = os.path.join(users_dir, folder)

                # Ищем файл .conf
                for file in os.listdir(folder_path):
                    if file.endswith('.conf'):
                        conf_path = os.path.join(folder_path, file)
                        private_ip, server_ip = extract_ips_from_conf(conf_path)

                        if private_ip and server_ip:
                            # Обновляем данные в базе данных
                            await db.execute('''
                                UPDATE users
                                SET private_ip = ?, server_ip = ?
                                WHERE chat_id = ?
                            ''', (private_ip, server_ip, chat_id))
                            await db.commit()

                            print(f"Обновлены данные для пользователя с chat_id {chat_id}: частный IP {private_ip}, серверный IP {server_ip}")
                        else:
                            print(f"Не удалось найти IP-адреса в конфигурационном файле для chat_id {chat_id}")