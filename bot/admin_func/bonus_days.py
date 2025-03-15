import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.admin_func.states import AdminStates
from bot.handlers.admin import send_admin_log
from bot.keyboards.reply import reply_keyboard
from models.UserCl import UserCl

router = Router()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("admin_actions.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# 📌 Обработчик нажатия на кнопку "Добавить бонусные дни"
@router.callback_query(F.data == "add_bonus_days")
async def handle_add_bonus_days(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор добавления бонусных дней."""
    try:
        data = await state.get_data()
        user = data.get("current_user")

        if user and user.servers:
            active_server = user.servers[0]  # Получаем первый активный сервер
            current_date_key_off = await active_server.date_key_off.get()

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Галя, у нас отмена", callback_data="search_user")]
            ])

            # Запрашиваем у админа количество бонусных дней
            await callback.message.answer(
                f"📆 Текущая дата окончания действия ключа: {current_date_key_off}\n"
                "🛠 Введите количество бонусных дней (1-50), которое хотите добавить, или нажмите 'Отмена'.",
                reply_markup=keyboard
            )
            await state.set_state(AdminStates.waiting_for_bonus_days)
        else:
            await callback.message.answer("❌ Ошибка: сначала выберите пользователя с активным сервером.")

        await callback.answer()

    except Exception as e:
        logger.error(f"⚠ Ошибка в `handle_add_bonus_days`: {e}")
        await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()


# 📌 Обработка ввода количества бонусных дней
@router.message(AdminStates.waiting_for_bonus_days)
async def process_bonus_days_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод количества бонусных дней."""
    try:
        # Проверяем, корректно ли введено число
        days_to_add = int(message.text.strip())
        if not (1 <= days_to_add <= 50):
            await message.answer("⚠ Введите число от 1 до 50.")
            return

        data = await state.get_data()
        us = data.get("current_user")

        if not us or not us.servers:
            await message.answer("❌ Ошибка: пользователь или сервер не найден.")
            await state.clear()
            return

        server = us.active_server

        # Получаем текущую дату отключения
        current_date_key_off_str = await server.date_key_off.get()
        now = datetime.now()

        try:
            current_date_key_off = datetime.strptime(current_date_key_off_str, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            current_date_key_off = now  # Если дата некорректна, устанавливаем текущую дату

        # Если ключ уже истек, продлеваем от текущей даты
        new_date_key_off = max(current_date_key_off, now) + timedelta(days=days_to_add)

        formatted_new_date = new_date_key_off.strftime("%d.%m.%Y %H:%M:%S")
        await server.date_key_off.set(formatted_new_date)

        # 🔹 Включаем пользователя, если он был отключен
        if not await server.enable.get():
            await server.enable.set(True)
            logger.info(f"🔄 Пользователь {us.chat_id} был выключен и теперь активирован.")

        # 🔥 Логирование и уведомление администраторов
        admin_log_message = (
            f"✅ <b>Админ {message.from_user.full_name} добавил {days_to_add} дней</b>\n"
            f"👤 <b>Пользователь:</b> {us.chat_id}\n"
            f"📆 <b>Новая дата окончания:</b> {formatted_new_date}\n"
            f"🔘 <b>Статус:</b> {'Активирован' if await server.enable.get() else 'Отключен'}"
        )
        await send_admin_log(bot=message.bot, message=admin_log_message)

        # 🔔 Уведомляем пользователя о продлении подписки
        user_message = (
            f"🎁 Вам добавлено <b>{days_to_add} бонусных дней!</b>\n"
            f"📅 <b>Новая дата окончания подписки:</b> {formatted_new_date}."
        )
        if await server.enable.get():
            user_message += "\n⚡ Ваш доступ активирован."

        try:
            await message.bot.send_message(chat_id=us.chat_id, text=user_message, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"❗ Ошибка при уведомлении пользователя {us.chat_id}: {e}")
            await send_admin_log(message.bot, f"❌ Ошибка при отправке уведомления пользователю {us.chat_id}")

        await state.clear()

    except ValueError:
        await message.answer("⚠ Введите корректное число дней.")
    except Exception as e:
        logger.error(f"❌ Ошибка в `process_bonus_days_input`: {e}")
        await message.answer("❌ Произошла ошибка при обработке данных.")
        await state.clear()
