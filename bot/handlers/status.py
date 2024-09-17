from aiogram import Router, types
from aiogram.filters import Command
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
from bot.utils.db import get_user_status
from datetime import datetime

router = Router()

@router.message(Command("status"))
@router.message(lambda message: message.text == "Информация об аккаунте ℹ️")
async def cmd_status(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    bot = message.bot

    # Сохраняем сообщение пользователя для удаления после отправки информации
    await store_message(chat_id, message.message_id, message.text, 'user')

    # Получаем данные пользователя из базы данных
    user_status = await get_user_status(user_id)

    if user_status:
        registration_date, user_name = user_status

        # Преобразуем строку в datetime, если это необходимо
        if isinstance(registration_date, str):
            registration_date = datetime.strptime(registration_date, "%Y-%m-%d %H:%M:%S.%f")

        # Вычисляем количество дней с момента регистрации
        now = datetime.now()
        days_since_registration = (now - registration_date).days
        seconds_since_registration = (now - registration_date).total_seconds()

        traffic_used_mb = 0  # Потраченный трафик (по умолчанию 0 MB)

        # Формируем сообщение в зависимости от прошедшего времени
        if days_since_registration == 0:
            hours_since_registration = seconds_since_registration // 3600
            minutes_since_registration = (seconds_since_registration % 3600) // 60

            if hours_since_registration > 0:
                status_message = (
                    f"🕒 Вы с нами уже **{int(hours_since_registration)} часов**! 🚀 Какой прогресс! 😎\n"
                    f"Дата регистрации: {registration_date.strftime('%d-%m-%Y')}\n"
                    f"Имя пользователя: {user_name}\n"
                    f"Потрачено трафика: **{traffic_used_mb} MB**"
                )
            elif minutes_since_registration > 0:
                status_message = (
                    f"🕒 Вы с нами уже **{int(minutes_since_registration)} минут**! 🚀 Какой прогресс! 😎\n"
                    f"Дата регистрации: {registration_date.strftime('%d-%m-%Y')}\n"
                    f"Имя пользователя: {user_name}\n"
                    f"Потрачено трафика: **{traffic_used_mb} MB**"
                )
            else:
                status_message = (
                    f"🕒 Вы с нами уже **{int(seconds_since_registration)} секунд**! 🚀 Какой прогресс! 😎\n"
                    f"Дата регистрации: {registration_date.strftime('%d-%m-%Y')}\n"
                    f"Имя пользователя: {user_name}\n"
                    f"Потрачено трафика: **{traffic_used_mb} MB**"
                )
        else:
            status_message = (
                f"🕒 Вы с нами уже **{days_since_registration} дней**! 🚀 Какой прогресс! 😎\n"
                f"Дата регистрации: {registration_date.strftime('%d-%m-%Y')}\n"
                f"Имя пользователя: {user_name}\n"
                f"Потрачено трафика: **{traffic_used_mb} MB**"
            )

        # Удаление старых сообщений с той же информацией
        for msg in messages_for_db:
            if msg['chat_id'] == chat_id and msg['message_text'] == status_message:
                try:
                    await bot.delete_message(chat_id, msg['message_id'])
                except Exception as e:
                    print(f"Не удалось удалить сообщение {msg['message_id']}: {e}")

        # Отправка нового сообщения с информацией об аккаунте
        sent_message = await message.answer(status_message, parse_mode="Markdown")

        if sent_message and sent_message.message_id:
            # Сохраняем и регистрируем сообщение только в случае успешной отправки
            await store_message(chat_id, sent_message.message_id, status_message, 'bot')
            await register_message_type(chat_id, sent_message.message_id, 'account_status','bot')
        else:
            print("Ошибка: сообщение не отправлено или нет message_id")

    else:
        # Отправка сообщения, если данные не найдены
        error_message = "Ваши данные не найдены в системе."
        sent_message = await message.answer(error_message)

        if sent_message and sent_message.message_id:
            await store_message(chat_id, sent_message.message_id, error_message, 'bot')
        else:
            print("Ошибка: сообщение не отправлено или нет message_id")

    # Удаление сообщения пользователя после обработки
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя {message.message_id}: {e}")

    # Удаляем неважные сообщения
    await delete_unimportant_messages(chat_id, bot)
