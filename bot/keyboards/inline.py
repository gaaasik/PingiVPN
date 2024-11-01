from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.admin import ADMIN_CHAT_IDS


# Создаем инлайн-кнопки для выбора устройства
# Создаем инлайн-кнопки для выбора устройства



# Клавиатура для скачивания приложения и подтверждения скачивания
def download_app_keyboard(device: str) -> InlineKeyboardMarkup:
    # Определяем ссылку для скачивания в зависимости от устройства
    if device.lower() == 'android':
        download_link = "https://play.google.com/store/apps/details?id=com.hiddify"
        instruction_link = "https://telegra.ph/Instrukciya-dlya-Android-01-01"
    elif device.lower() == 'iphone':
        download_link = "https://apps.apple.com/us/app/streisand/id6450534064"
        instruction_link = "https://telegra.ph/Podklyuchenie-PingiVPN-na-iPhone-11-01"
    elif device.lower() == 'mac':
        download_link = "https://apps.apple.com/us/app/foxray/id6448898396"
        instruction_link = "https://telegra.ph/Instrukciya-dlya-Mac-01-01"
    elif device.lower() == 'linux':
        download_link = "https://github.com/MatsuriDayo/nekoray/"
        instruction_link = "https://telegra.ph/Instrukciya-dlya-Linux-01-01"
    elif device.lower() == 'windows':
        download_link = "https://apps.microsoft.com/detail/9pdfnl3qv2s5?hl=ru-ru&gl=RU"
        instruction_link = "https://telegra.ph/Instrukciya-dlya-Windows-01-01"
    else:
        download_link = "#"
        instruction_link = "#"

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Открыть магазин приложений", url=download_link)],  # Ведет на ссылку для скачивания
        [InlineKeyboardButton(text="📷 Инструкция с картинками", url=instruction_link)],  # Ссылка на статью в Telegraph
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
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


#def keyborad_get_email(){}

def create_payment_button(chat_id):
    # Создаем инлайн-кнопку с текстом "Оплатить 199 рублей" и ссылкой на оплату
    payment_button = InlineKeyboardButton(text="Подключить подписку - 199р", callback_data="payment_199")
    if chat_id in ADMIN_CHAT_IDS:
        # Создаем клавиатуру и добавляем кнопку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[payment_button]
            , [InlineKeyboardButton(text="Удалить себя из базы данных - опасная кнопка!",
                                    callback_data='delete_user')]])
    else:
        # Создаем клавиатуру и добавляем кнопку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[payment_button]])

    return keyboard


def create_feedback_keyboard():
    buttons = [
        # Первый ряд кнопок: Плохо и Отлично
        [
            InlineKeyboardButton(text="Плохо", callback_data="feedback_bad"),
            InlineKeyboardButton(text="Отлично", callback_data="feedback_excellent")
        ],
        # Второй ряд кнопок: Поделиться с другом и Оплатить 199 рублей
        [
            InlineKeyboardButton(text="Поделиться с другом", callback_data="share_friend"),

        ],
        [InlineKeyboardButton(text="Оплатить 199 рублей", callback_data="pay_199")]
    ]

    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def account_info_keyboard():
    # Создаем инлайн-кнопку
    buttons = [
        [
            InlineKeyboardButton(text="Информация об аккаунте ℹ️", callback_data="account_info")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_inline_keyboard():
    # Создание клавиатуры с кнопками
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys"), InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="📨 Пригласить", callback_data="share"), InlineKeyboardButton(text="ℹ️ Всё о PingiVPN", callback_data="about_vpn")],
        [InlineKeyboardButton(text="🔌 Подключить VPN", callback_data="connect_vpn")]
    ]
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
