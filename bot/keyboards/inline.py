from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📜 Подробная инструкция", callback_data="detailed_instruction")]
    ]
)

# Создаем инлайн-кнопки для выбора устройства
def device_choice_keyboard():
    """Клавиатура для выбора устройства"""
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
        ]
    ]

    # Передаем список кнопок в InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

# Клавиатура для скачивания приложения и подтверждения скачивания
def download_app_keyboard(download_link):
    buttons = [
        [InlineKeyboardButton(text="Скачать", url=download_link)],  # Ведет на ссылку для скачивания
        [InlineKeyboardButton(text="Я скачал ✅", callback_data="app_downloaded")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)  # Передаем список кнопок в конструктор
    return keyboard

# Клавиатура для получения конфигурационного файла или QR-кода
def config_or_qr_keyboard():
    buttons = [
        [InlineKeyboardButton(text="Получить файл", callback_data="get_config"),
         InlineKeyboardButton(text="Показать QR-код", callback_data="get_qr_code")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)  # Передаем список кнопок в конструктор
    return keyboard