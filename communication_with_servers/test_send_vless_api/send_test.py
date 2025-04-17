import logging

from communication_with_servers.test_send_vless_api.XUIApiClient import VlessApiProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ],
    encoding="utf-8"
)
my_logging = logging.getLogger(__name__)

async def test_toggle_vpn_user():
    from communication_with_servers.test_send_vless_api.base_class import my_logging
    my_logging.info(" Запускается тестовое включение пользователя через API")

    processor = VlessApiProcessor()

    email = "PingiVPN_39000_Britain"

    task_data = {
        "email_key": email,
        "enable": False,
        "chat_id": 123456789
    }

    await processor.process_change_enable_user(task_data)