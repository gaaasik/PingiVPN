from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура для поиска пользователя
async def get_search_user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ввести Chat ID", callback_data="search_by_chat_id")],
        [InlineKeyboardButton(text="Вывести статистику", callback_data="show_statistics")],
        [InlineKeyboardButton(text="Заглушка: Ввести никнейм", callback_data="search_by_nickname")],
        [InlineKeyboardButton(text="Заглушка: Ввести номер телефона", callback_data="search_by_phone")],
        [InlineKeyboardButton(text="Заглушка: Ввести имя пользователя", callback_data="search_by_username")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_service")]
    ])

# Клавиатура для действий с найденным пользователем
async def get_user_service_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить бонусные дни", callback_data="add_bonus_days")],
        [InlineKeyboardButton(text="Включить пользователя", callback_data="enable_user")],
        [InlineKeyboardButton(text="Выключить пользователя", callback_data="disable_user")],
        [InlineKeyboardButton(text="Заглушка: Изменить конфигурационный ключ", callback_data="change_config_key")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_service")]
    ])
