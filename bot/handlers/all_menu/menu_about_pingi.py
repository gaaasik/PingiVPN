from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()
# Текст сообщения "Все о Pingi VPN"
about_pingi_text = (
    "*Все о Pingi VPN*\n\n"
    "Выберите интересующую вас информацию:\n\n"
)

protection_text = (
    "🔒 *Полная безопасность с Pingi VPN*\n\n"
    "Мы используем протокол *VLESS*, специально разработанный для обхода блокировок и защиты вашего трафика. "
    "VLESS работает по схеме клиент-сервер: ваше устройство отправляет запросы через сервер VPN, который "
    "направляет их на целевой сайт или приложение.\n\n"
    "✨ *Минимальная нагрузка и высокая скорость* — каждый пакет содержит только необходимые данные для аутентификации и маршрутизации, "
    "обеспечивая быстрое и стабильное соединение. Сессии устанавливаются без лишних процедур, что снижает задержку и "
    "делает работу более эффективной.\n\n"
    "🔐 *TLS шифрование* защищает ваши данные от перехвата и анализа, сохраняя приватность и безопасность.\n\n"
    "💡 С VLESS ваш трафик остаётся защищённым и скрытым от сторонних глаз на каждом этапе!\n\n"
    "📚 Подробнее о протоколе [VLESS](https://xtls.github.io/ru/development/protocols/vless.html)"
)

speed_text = (
    "🚀 *Ограничения и трафик*\n\n"
    "С Pingi VPN вы получаете *200GB* трафика в месяц, что вполне достаточно для большинства пользователей: "
    "просмотра видео, соцсетей и веб-серфинга.\n\n"
    "Если вы один из немногих, кому нужно больше трафика, мы предлагаем дополнительные пакеты — всегда готовы "
    "поддержать ваших активных пользователей. Выберите нужное и оставайтесь на связи без ограничений!"
)

pricing_text = (
    "💸 *Доступные тарифы и бонусы*\n\n"
    "Pingi VPN предлагает гибкие тарифы и возможности. Попробуйте VPN бесплатно в течение *7 дней* и оцените "
    "все преимущества!\n\n"
    "🗓 Подписка на 30 дней стоит всего *199₽*. Хотите больше бонусов? Приглашайте друзей и делитесь ссылками "
    "в соцсетях, чтобы получать дополнительные дни!\n\n"
    "💼 Мы открыты для сотрудничества. Если вас интересует партнерская программа — обращайтесь, "
    "и мы поможем вам заработать вместе с Pingi VPN!"
)

story_text = (
    "🐧 *История Pingi из Антарктиды*\n\n"
    "Когда-то в Антарктиде жил талантливый пингвин по имени Пинги. Однажды он нашел старый ноутбук и, "
    "учившись по статьям из открытого интернета, создал свой первый VPN сервер прямо на айсберге.\n\n"
    "Сначала его серверы были построены изо льда и снега, но со временем он научился создавать их "
    "из металла, как это делают люди. Это стало основой его успеха! 🛠️ Теперь его сеть серверов обеспечивает "
    "доступ к интернету по всему миру. \n\n"
    "🌐 Первый клич Пинги через интернет достиг его друзей, а затем распространился на все уголки планеты. "
    "Сегодня Pingi VPN продолжает дело своего создателя, помогая людям наслаждаться свободным интернетом!"
)

# Функция создания клавиатуры для каждого раздела с кнопками "Назад" и "Главное меню"
def about_pingi_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔒 Защита данных", callback_data="about_protection")],
        [InlineKeyboardButton(text="🚀 Какие ограничения?", callback_data="about_speed")],
        [InlineKeyboardButton(text="💰 Сколько это стоит?", callback_data="about_pricing")],
        [InlineKeyboardButton(text="❄️ История Pingi из Антарктиды", callback_data="about_story")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Кнопки "Назад" и "Главное меню" для каждого сообщения
def back_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="about_pingi")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Обработчики для каждой кнопки

@router.callback_query(lambda c: c.data == "about_protection")
async def handle_about_protection(callback_query: CallbackQuery):
    await callback_query.message.edit_text(protection_text, reply_markup=back_main_keyboard(), parse_mode="Markdown", disable_web_page_preview=True)
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "about_speed")
async def handle_about_speed(callback_query: CallbackQuery):
    await callback_query.message.edit_text(speed_text, reply_markup=back_main_keyboard(), parse_mode="Markdown")
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "about_pricing")
async def handle_about_pricing(callback_query: CallbackQuery):
    await callback_query.message.edit_text(pricing_text, reply_markup=back_main_keyboard(), parse_mode="Markdown")
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "about_story")
async def handle_about_story(callback_query: CallbackQuery):
    await callback_query.message.edit_text(story_text, reply_markup=back_main_keyboard(), parse_mode="Markdown")
    await callback_query.answer()


# Обработчик для команды "/about" и кнопки "Все о Pingi VPN"
@router.callback_query(lambda c: c.data == "about_pingi")
async def handle_about_pingi(event: types.Message | CallbackQuery):
    if isinstance(event, types.Message):
        await event.answer(about_pingi_text, reply_markup=about_pingi_keyboard(), parse_mode="Markdown")
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(about_pingi_text, reply_markup=about_pingi_keyboard(), parse_mode="Markdown")
        await event.answer()



