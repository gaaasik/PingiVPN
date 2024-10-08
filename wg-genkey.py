import os
import subprocess
import qrcode

# Директория для сохранения файлов конфигурации и QR-кодов
output_dir = "configs_wg"
os.makedirs(output_dir, exist_ok=True)

# Параметры WireGuard
endpoint = "85.92.108.98:51820"
dns = "1.1.1.1"
server_public_key = "CCdVBAh6VBgNEYAPiU0lzYKiwMbPxc47S2gTQxxnCFU="
allowed_ips = "0.0.0.0/0, ::/0"


def generate_keys():
    # Генерация приватного ключа
    private_key = subprocess.check_output("wg genkey", shell=True).decode().strip()
    # Генерация публичного ключа
    public_key = subprocess.check_output(f"echo {private_key} | wg pubkey", shell=True).decode().strip()
    # Генерация preshared key
    preshared_key = subprocess.check_output("wg genpsk", shell=True).decode().strip()
    return private_key, public_key, preshared_key


def generate_config(index, private_key, preshared_key, address):
    # Создание содержимого конфигурационного файла
    config = f"""
[Interface]
PrivateKey = {private_key}
Address = {address}/24
DNS = {dns}

[Peer]
PublicKey = {server_public_key}
PresharedKey = {preshared_key}
AllowedIPs = {allowed_ips}
PersistentKeepalive = 25
Endpoint = {endpoint}
"""
    return config


def save_config_and_qr(index, config):
    conf_filename = f"{output_dir}/1851{str(index).zfill(3)}_free.conf"
    qr_filename = f"{output_dir}/1851{str(index).zfill(3)}_free.png"

    # Сохранение конфигурационного файла
    with open(conf_filename, 'w') as conf_file:
        conf_file.write(config)

    # Генерация QR-кода
    qr = qrcode.make(config)
    qr.save(qr_filename)
    print(f"Сохранен файл: {conf_filename} и QR-код: {qr_filename}")


def main():
    base_ip = "10.8.0."
    for i in range(3, 53):  # Генерация 50 конфигураций
        address = f"{base_ip}{i + 1}"  # Увеличиваем IP-адрес для каждого клиента
        private_key, public_key, preshared_key = generate_keys()
        config = generate_config(i, private_key, preshared_key, address)
        save_config_and_qr(i, config)


if __name__ == "__main__":
    main()
