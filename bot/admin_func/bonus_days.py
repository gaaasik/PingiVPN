import logging

from aiogram import Router, types,F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from bot.admin_func.states import AdminStates
from bot.handlers.admin import send_admin_log
from models.UserCl import UserCl

router = Router()

@router.callback_query(F.data == "add_bonus_days")
async def handle_add_bonus_days(callback, state: FSMContext):
    """Обрабатывает выбор добавления бонусных дней."""
    data = await state.get_data()
    user = data.get("current_user")

    if user and user.servers:
        # Получаем дату окончания ключа
        active_server = user.servers[0]
        current_date_key_off = await active_server.date_key_off.get()

        # Отправляем дату окончания перед добавлением бонусных дней
        await callback.message.answer(
            f"Текущая дата окончания действия ключа: {current_date_key_off}\n"
            "Введите количество бонусных дней, которое хотите добавить, или нажмите 'Отмена'."
        )
        await state.set_state(AdminStates.waiting_for_bonus_days)
    else:
        await callback.message.answer("Сначала выберите пользователя с активным сервером.")
    await callback.answer()


@router.message(AdminStates.waiting_for_bonus_days)
async def process_bonus_days_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод количества бонусных дней."""
    try:
        days_to_add = int(message.text.strip())
        if days_to_add <= 0 or days_to_add > 50:
            await message.answer("Введите число от 1 до 50.")
            return

        #us = await UserCl.load_user(chat_id)


        data = await state.get_data()
        us = data.get("current_user")
        user = await UserCl.load_user(message.chat.id)

        if not us or not us.servers:
            await message.answer("Ошибка: пользователь или сервер не найден.")
            await state.clear()
            return

        server = us.active_server

        current_date_key_off_str = await server.date_key_off.get()

        # Конвертация даты из строки в datetime
        current_date_key_off = datetime.strptime(current_date_key_off_str, "%d.%m.%Y %H:%M:%S")
        now = datetime.now()

        # Если ключ уже истек, берем сегодняшнюю дату как основу
        if current_date_key_off < now:
            new_date_key_off = now + timedelta(days=days_to_add)
            logging.info(f"Ключ истек, новая дата: {new_date_key_off.strftime('%d.%m.%Y %H:%M:%S')}")
        else:
            new_date_key_off = current_date_key_off + timedelta(days=days_to_add)
            logging.info(f"Ключ активен, новая дата: {new_date_key_off.strftime('%d.%m.%Y %H:%M:%S')}")

        formatted_new_date = new_date_key_off.strftime("%d.%m.%Y %H:%M:%S")
        await server.date_key_off.set(formatted_new_date)
#+++++++++++++++++++++++++++++++++++++++++++
        # Если пользователь был отключен, активируем его
        if not await server.enable.get():
            await server.enable.set(True)
            logging.info(f"Пользователь {us.chat_id} был выключен. Сейчас Активирован.")

        # Уведомляем администраторов
        await send_admin_log(
            bot=message.bot,
            message=(
                f"✅ Администратор {message.from_user.full_name} добавил {days_to_add} дней "
                f"пользователю с Chat ID {us.chat_id}.\n"
                f"🔑 Новая дата окончания: {formatted_new_date}.\n"
                f"🔘 Пользователь активирован: {await server.enable.get()}"
            )
        )

        # Формируем сообщение
        message_text = (
            f"🔹 Вам добавлено {days_to_add} бонусных дней!\n"
            f"📅 Новая дата окончания ключа: <b>{formatted_new_date}</b>."
        )

        # Добавляем информацию о включении доступа, только если пользователь был отключен
        if await server.enable.get():
            message_text += "\n⚡ Ваш доступ активирован."

        # Уведомляем пользователя, если текст не пустой
        if message_text.strip():
            try:
                await message.bot.send_message(
                    chat_id=us.chat_id,
                    text=message_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.warning(f"Ошибка при уведомлении пользователя {us.chat_id}: {e}")
                await send_admin_log(message.bot, f"❌ Ошибка при уведомлении пользователя {us.chat_id}")
        else:
            logging.warning(f"Не отправляем пустое сообщение пользователю {us.chat_id}")

        await state.clear()
    except ValueError:
        await message.answer("Введите корректное число дней.")
    except Exception as e:
        logging.error(f"Ошибка при добавлении бонусных дней: {e}")
        await message.answer("Произошла ошибка при обработке данных.")
        await state.clear()