import logging

from aiogram import Router, types,F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from bot.admin_func.states import AdminStates

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
        # Проверяем корректность ввода
        days_to_add = int(message.text.strip())
        if days_to_add <= 0 and days_to_add <50:
            await message.answer("Количество дней должно быть положительным числом и меньше 50. Попробуйте снова.")
            return

        # Получаем данные о текущем пользователе
        data = await state.get_data()
        user = data.get("current_user")

        if not user or not user.servers:
            await message.answer("Ошибка: пользователь или сервер не найден.")
            await state.clear()
            return

        # Обновляем дату окончания
        active_server = user.servers[0]
        current_date_key_off = await active_server.date_key_off.get()

        # Конвертация даты
        new_date_key_off = datetime.strptime(current_date_key_off, "%d.%m.%Y %H:%M:%S") + timedelta(days=days_to_add)
        formatted_new_date = new_date_key_off.strftime("%d.%m.%Y %H:%M:%S")

        # Сохраняем новую дату окончания
        await active_server.date_key_off.set(formatted_new_date)


        # Уведомляем всех администраторов
        from bot.handlers.admin import send_admin_log
        await send_admin_log(
            bot=message.bot,
            message=(
                f"Администратор {message.from_user.full_name} добавил {days_to_add} дней "
                f"пользователю с Chat ID {user.chat_id}. Новая дата окончания: {formatted_new_date}."
            )
        )

        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                chat_id=user.chat_id,
                text=(
                    f"Вам добавлено {days_to_add} бонусных дней. Новая дата окончания действия ключа: "
                    f"<b>{formatted_new_date}</b>."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            await send_admin_log(message.bot, "Не удалось отправить уведомление пользователю о добавлении бонусных дней")
            logging.warning(f"Не удалось уведомить пользователя {user.chat_id}: {e}")

        # Возвращаемся к выбору действия
        await state.set_state(AdminStates.waiting_for_action)

    except ValueError:
        await message.answer("Введите корректное число дней.")
    except Exception as e:
        logging.error(f"Ошибка при добавлении бонусных дней: {e}")
        await message.answer("Произошла ошибка при обработке данных.")
        await state.clear()