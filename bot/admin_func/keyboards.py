from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔍 Меню поиска пользователя
async def get_search_user_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔢 Поиск по Chat ID", callback_data="search_by_chat_id")],
        [InlineKeyboardButton(text="🆔 Поиск по никнейму (скоро)", callback_data="search_by_nickname")],
        [InlineKeyboardButton(text="📞 Поиск по телефону (скоро)", callback_data="search_by_phone")],
        [InlineKeyboardButton(text="📛 Поиск по имени (скоро)", callback_data="search_by_username")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_service")]
    ])

# ⚙️ Меню действий с пользователем
async def get_user_service_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить бонусные дни", callback_data="add_bonus_days")],
        [InlineKeyboardButton(text="✅ Включить пользователя", callback_data="enable_user")],
        [InlineKeyboardButton(text="❌ Выключить пользователя", callback_data="disable_user")],
        [InlineKeyboardButton(text="🔄 Перезапуск соединения (скоро)", callback_data="restart_connection")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_service")]
    ])
# 📊 Кнопки для статистики
async def get_statistics_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Выбрать дату", callback_data="choose_stat_date")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_service")]
    ])

# 🔧 Главное меню режима обслуживания
async def get_service_mode_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="search_user")],
        [InlineKeyboardButton(text="📊 Вывести статистику", callback_data="show_statistics")],
        [InlineKeyboardButton(text="⚙️ Админ-настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="❌ Выйти из режима обслуживания", callback_data="exit_service_mode")]
    ])

