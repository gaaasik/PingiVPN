from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.admin import send_admin_log

router = Router()
# Текст сообщения "Все о Pingi VPN"
about_pingi_text = (
    "*Все о Pingi VPN*\n\n"
    "Выберите интересующую вас информацию:\n\n"
)
protection_text = (
    "🔒 *Полная безопасность с Pingi VPN*\n\n"
    "🛡 Мы используем протокол *WireGuard*, который является современным и максимально лёгким VPN-решением. "
    "WireGuard построен на основе передовых криптографических алгоритмов и обеспечивает защиту вашего трафика с минимальной нагрузкой на устройство.\n\n"
    "✨ *Молниеносная скорость и низкая задержка* — благодаря минималистичному дизайну протокола, обмен данными происходит быстро и эффективно. "
    "Каждое соединение оптимизировано для обеспечения стабильности и производительности, даже при высокой нагрузке.\n\n"
    "🔐 *Шифрование на основе современных стандартов* — WireGuard использует такие алгоритмы, как ChaCha20 и Poly1305, чтобы надёжно защищать ваши данные от перехвата и анализа, "
    "гарантируя полную конфиденциальность.\n\n"
    "💡 С WireGuard ваш трафик остаётся защищённым и скрытым от сторонних глаз, а соединение — стабильным и безопасным!\n\n"
    "📚 Подробнее о протоколе [WireGuard](https://www.wireguard.com/)"
)

speed_text = (
    "🚀 *Ограничения и трафик*\n\n"
    "💼 С Pingi VPN вы получаете *200GB* трафика в месяц, что вполне достаточно для большинства пользователей: "
    "просмотра видео, соцсетей и веб-серфинга.\n\n"
    "🎁 Если вы один из немногих, кому нужно больше трафика, в будщем будут доступны дополнительные пакеты трафика \n"
    "Мы всегда готовы "
    "поддержать наших активных пользователей."
)

pricing_text = (
    "💸 *Доступные тарифы и бонусы*\n\n"
    "🎉 Попробуйте VPN бесплатно в течение *7 дней* и оцените "
    "все преимущества!\n\n"
    "🗓 Подписка на 30 дней стоит как стакан кофе *199₽*. Хотите больше бонусов? \n\n"
    "👥 Приглашайте друзей и делитесь ссылками "
    "в соцсетях, чтобы получать дополнительные дни!"
    " Ведь мы правда предоставляем быстрый и рабочий VPN\n\n"
    "🤝 Мы открыты для сотрудничества. Если вас интересует партнерская программа — обращайтесь, "
    "и мы поможем вам заработать вместе с Pingi VPN!"
)

story_text = (
    "🐧 *История Pingi из Антарктиды*\n\n"
    "❄️ Когда-то в Антарктиде жил талантливый пингвин по имени Пинги. Однажды он нашел старый ноутбук и, "
    "учившись по статьям из открытого интернета, создал свой первый VPN сервер прямо на айсберге.\n\n"
    "🛠️ Сначала его серверы были построены изо льда и снега, но со временем он научился создавать их "
    "из металла, как это делают люди. Это стало основой его успеха! Теперь его сеть серверов обеспечивает "
    "доступ к интернету по всему миру.\n\n"
    "🌐 Первый клич Пинги через интернет достиг его друзей, а затем распространился на все уголки планеты. "
    "Сегодня Pingi VPN продолжает дело своего создателя, помогая людям наслаждаться свободным интернетом!"
)

# Функция создания клавиатуры для каждого раздела с кнопками "Назад" и "Главное меню"
def about_pingi_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔒 Безопасность", callback_data="about_protection"),
        InlineKeyboardButton(text="🧱 Ограничения", callback_data="about_speed")],
        [InlineKeyboardButton(text="💰 Сколько это стоит?", callback_data="about_pricing")],
        [InlineKeyboardButton(text="❄️ История Pingi из Антарктиды", callback_data="about_story")],
        [InlineKeyboardButton(text="🎁 Участвовать в розыгрыше", callback_data="lottery_entry")],  # 👈 добавлено
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
    # Логируем количество ошибок после обработки батча
    await send_admin_log(callback_query.bot, f"{callback_query.from_user.id} Начал читать историю про пингвина")
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



