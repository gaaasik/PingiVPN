from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.admin import ADMIN_CHAT_IDS


# Создаем инлайн-кнопки для выбора устройства
# Создаем инлайн-кнопки для выбора устройства



# Клавиатура для скачивания приложения и подтверждения скачивания
def download_app_keyboard(download_link):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть магазин приложений", url=download_link)],  # Ведет на ссылку для скачивания
        [InlineKeyboardButton(text="Инструкция с картинками", callback_data="a")],
        [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
    ])
    return keyboard


     # Передаем список кнопок в конструктор
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
        [InlineKeyboardButton(text="Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="Мои ключи", callback_data="my_keys"), InlineKeyboardButton(text="Помощь", callback_data="help")],
        [InlineKeyboardButton(text="Пригласить", callback_data="share"), InlineKeyboardButton(text="Всё о PingiVPN", callback_data="about_vpn")],
        [InlineKeyboardButton(text="Подключить VPN", callback_data="connect_vpn")]
    ]
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
