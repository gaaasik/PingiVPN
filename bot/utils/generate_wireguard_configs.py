# import os
# import qrcode
# from datetime import datetime
#
# from aiogram.types import FSInputFile
#
# # Путь к директории для сохранения конфигураций и QR-кодов
# CONFIGS_DIR = 'configs'
#
# # Убедитесь, что директория существует
# if not os.path.exists(CONFIGS_DIR):
#     os.makedirs(CONFIGS_DIR)
# def generate_wireguard_config(phone_number):
#     """
#     Генерирует файл конфигурации WireGuard и соответствующий QR-код для пользователя.
#     """
#     user_dir = os.path.join(CONFIGS_DIR, phone_number)
#
#     # Убедитесь, что директория существует
#     if not os.path.exists(user_dir):
#         os.makedirs(user_dir)
#
#     # Генерация ключей для WireGuard
#     private_key, public_key = generate_keypair()
#
#     # Определение пути для файла конфигурации и QR-кода
#     config_filename = os.path.join(user_dir, f"{phone_number}_free.conf")
#     qr_filename = os.path.join(user_dir, f"{phone_number}_free.png")
#
#     # Содержание файла конфигурации
#     config_content = f"""
# [Interface]
# PrivateKey = {private_key}
# Address = 10.0.0.2/24
# DNS = 1.1.1.1
#
# [Peer]
# PublicKey = SERVER_PUBLIC_KEY
# Endpoint = YOUR_SERVER_IP:51820
# AllowedIPs = 0.0.0.0/0, ::/0
# """
#
#     # Запись файла конфигурации
#     with open(config_filename, 'w') as config_file:
#         config_file.write(config_content)
#
#     # Генерация QR-кода
#     qr = qrcode.make(config_content)
#     qr.save(qr_filename)
#
#     return FSInputFile(config_filename), FSInputFile(qr_filename)