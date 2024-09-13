import os

CONFIGS_DIR = r'C:\PycharmProjects\VPN_BOT\configs'
BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')
PATH_TO_IMAGES = r'C:\PycharmProjects\VPN_BOT\data\photo'
REGISTERED_USERS_DIR = os.path.join(CONFIGS_DIR, 'registered_user')
name_bot = 'PingiVPN_bot'
# Путь к базе данных
database_path_local = r'C:\PycharmProjects\vpn_bot.db'

# Пример важного сообщения
welcome_message = (
    "👋 Добро пожаловать на Антарктиду интернета!\n\n"
    "🎯 Здесь тебе рады, а еще всё просто и удобно! \n"
    "🚀 Подключайтесь к нашему VPN и забудьте о сложностях. 😤\n\n"
    
   # "Никаких ограничений, только свобода! 🎉\n\n"
    "🔗 Как запустить: Нажмите на кнопку ниже 👇 \n\n"
    "🛡️ Скорость на высоте, минимальные потери! 💡 \n 🚀 А безопасность и анонимность — на высшем уровне! 🔒\n\n"
    "🙌 Поделитесь нашим ботом с друзьями и получите бонус за каждого приглашенного! 👇👇👇\n"
)


instructions_message = (
    "❗️ *Инструкция* ❗️\n\n"
    "🔒 Для подключения VPN:\n\n"
    "1. 📲 *Скачайте приложение WireGuard:* \n"
    "[IPhone](https://apps.apple.com/us/app/wireguard/id1441195209) | "
    "[Android](https://play.google.com/store/apps/details?id=com.wireguard.android) | "
    "[Windows](https://www.wireguard.com/install/) \n\n"
    "2. 💾 *Скачайте файл конфигурации или отсканируйте QR код с помощью друга.*\n Вы можете переслать ему изображение и отсканировать\n"
    "3. 🛡 *Пользуйтесь безопасным соединением!*\n\n"
)

detailed_instructions_message = (
    "📜 *Подробная инструкция* 📜\n\n"
    "Для использования нашего VPN, вам необходимо:\n\n"
    "1. Установить приложение WireGuard на ваше устройство.\n"
    "2. Сканировать QR-код с конфигурацией, который мы вам отправили. Вы можете сделать это используя приложение WireGuard. \n QR код можно переслать другу или на другое устройство \n"
    "3. Загрузить конфигурацию в приложении и задать имя pingi_vingi.\n\n"
    "После этого вы можете пользоваться)\n"
    "Если у вас возникнут вопросы, не стесняйтесь обращаться к нашей поддержке.😊"

)

unknow_message = ("К сожалению я вас не понимаю.. \n\n")

