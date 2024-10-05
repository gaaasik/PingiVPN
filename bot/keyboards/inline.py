from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
############################################################Анатолий#######################################
from bot.payments.pay_199 import create_payment199
############################################################Анатолий#######################################

# Создаем инлайн-кнопки для выбора устройства
def device_choice_keyboard(message):
    user_id = message.from_user.id
    """Клавиатура для выбора устройства"""
############################################################Анатолий#######################################
    payment_url = create_payment199(message)
############################################################Анатолий#######################################
    # Создаем кнопки
    buttons = [
        [
            InlineKeyboardButton(text="Android", callback_data="device_android"),
            InlineKeyboardButton(text="iPhone", callback_data="device_iphone")
        ],
        [
            InlineKeyboardButton(text="Mac", callback_data="device_mac"),
            InlineKeyboardButton(text="Linux", callback_data="device_linux")
        ],
        [
            InlineKeyboardButton(text="Windows", callback_data="device_windows")
        ],
############################################################Анатолий#######################################
        [
            InlineKeyboardButton(text="Оплатить бота",  url=payment_url)
        ]
############################################################Анатолий#######################################
    ]

    # Передаем список кнопок в InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

# Клавиатура для скачивания приложения и подтверждения скачивания
def download_app_keyboard(download_link):
    buttons = [
        [InlineKeyboardButton(text="Открыть магазин приложений", url=download_link)],  # Ведет на ссылку для скачивания
        [InlineKeyboardButton(text="Я скачал ✅", callback_data="app_downloaded")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)  # Передаем список кнопок в конструктор
    return keyboard

# Кнопка для перехода на канал и кнопка для проверки подписки
def subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти на канал", url="https://t.me/pingi_hub")],
        [InlineKeyboardButton(text="Я подписался", callback_data="check_subscription")]
    ])
    return keyboard

# Функция для кнопки "Получить файл"
def get_file_button():
    return InlineKeyboardButton(text="Получить файл", callback_data="get_config")

# Функция для кнопки "Показать QR-код"
def get_qr_code_button():
    return InlineKeyboardButton(text="Показать QR-код", callback_data="get_qr_code")

# Функция для кнопки "Подробная инструкция"
def get_detailed_instruction_button():
    return InlineKeyboardButton(
        text="📜 Подробная инструкция",
        url="https://telegra.ph/Podrobnaya-instrukciya-po-podklyucheniyu-k-Pingi-VPN-09-17"
    )
# Основная функция для формирования клавиатуры
def config_or_qr_keyboard():
    buttons = [
        [get_file_button(), get_qr_code_button()],
        [get_detailed_instruction_button()]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)