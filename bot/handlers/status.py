from aiogram import Router, types
from aiogram.filters import Command

from bot.handlers.cleanup import delete_unimportant_messages, store_message, register_message_type, \
    delete_message_with_type
from bot.keyboards.inline import create_payment_button
from bot.database.db import get_days_since_registration_db
from bot.database.users_db import get_user_registration_date_and_username_db
from models.UserCl import UserCl

#from bot.utils.file_sender import count_files_in_directory

router = Router()


# @router.message(Command("status"))
# @router.message(lambda message: message.text == "Информация об аккаунте ℹ️")
# async def cmd_status(message: types.Message):
#     user_id = message.from_user.id
#     bot = message.bot
#     chat_id = message.chat.id
#
#
#     # Сохраняем сообщение пользователя для удаления после отправки информации
#     await store_message(chat_id, message.message_id, message.text, 'user')
#
#     # Получаем данные пользователя из базы данных
#     user_data = await get_user_registration_date_and_username(user_id)  # Получаем статус и дату регистрации
#     if user_data and len(user_data) == 4:  # Проверяем, что возвращено 4 элемента
#         registration_date, days_since_registration, user_name, subscription_status = user_data
#
#         # Код для отправки сообщения с кнопкой оплаты
#         if subscription_status == "waiting_pending":
#             status_sub_txt = f"Ожидание оплаты подписки"
#             # Создаем клавиатуру с кнопкой оплаты
#             keyboard = create_payment_button(chat_id)
#
#         elif subscription_status == 'new_user' :
#             status_sub_txt = f"Пробный период"
#             keyboard = create_payment_button(chat_id)
#
#
#         elif subscription_status == 'active' :
#             status_sub_txt = f'Подписка активна'
#             keyboard = create_payment_button(chat_id)
#         else:
#             status_sub_txt = subscription_status
#             keyboard = create_payment_button(chat_id)
#
#             # Пример экранирования текста
#         status_message = (
#             f"🕒 Вы с нами уже {(str(days_since_registration))} дней! 🚀 Какой прогресс! 😎\n"
#             f"Действие тарифа: {(days_since_registration)} дней \n"
#             f"Имя пользователя: {(user_name)}\n"
#             f"Статус подписки: *{(status_sub_txt)}*"
#         )
# ############################################################################
#         # Удаление старых сообщений с той же информацией
#         for msg in messages_for_db:
#             if msg['chat_id'] == chat_id and msg['message_text'] == status_message:
#                 try:
#                     await bot.delete_message(chat_id, msg['message_id'])
#                 except Exception as e:
#                     print(f"Не удалось удалить сообщение {msg['message_id']}: {e}")
#
#         # Отправка нового сообщения с информацией об аккаунте и кнопкой оплаты, если нужно
#         sent_message = await message.answer(status_message, parse_mode="Markdown", reply_markup=keyboard)
#
#
#         if sent_message and sent_message.message_id:
#             # Сохраняем и регистрируем сообщение только в случае успешной отправки
#             await store_message(chat_id, sent_message.message_id, status_message, 'bot')
#             await register_message_type(chat_id, sent_message.message_id, 'account_status', 'bot')
#         else:
#             print("Ошибка: сообщение не отправлено или нет message_id")
#
#     else:
#         # Отправка сообщения, если данные не найдены
#         error_message = "Ваши данные не найдены в системе. Обратитесь в поддержку, мы на связи."
#         sent_message = await message.answer(error_message)
#
#         if sent_message and sent_message.message_id:
#             await store_message(chat_id, sent_message.message_id, error_message, 'bot')
#         else:
#             print("Ошибка: сообщение не отправлено или нет message_id")
#
#     # Удаление сообщения пользователя после обработки
#     try:
#         await bot.delete_message(chat_id, message.message_id)
#     except Exception as e:
#         print(f"Не удалось удалить сообщение пользователя {message.message_id}: {e}")
#
#     # Удаляем неважные сообщения
#     await delete_unimportant_messages(chat_id, bot)# Обработчик для инлайн-кнопки
#

@router.message(Command("status"))
@router.message(lambda message: message.text == "Информация об аккаунте ℹ️")
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    bot = message.bot
    chat_id = message.chat.id

    # Сохраняем сообщение пользователя для удаления после отправки информации.
    await store_message(chat_id, message.message_id, message.text, 'user')

    # Используем функцию generate_status_message для получения текста и клавиатуры.
    status_message, keyboard = await generate_status_message(user_id)

    # Удаляем старые сообщения с информацией о статусе.
    await delete_message_with_type(chat_id, 'account_status', bot)

    # Отправляем новое сообщение с информацией об аккаунте и кнопкой оплаты, если она есть.
    sent_message = await message.answer(status_message, parse_mode="Markdown", reply_markup=keyboard)

    # Сохраняем сообщение в базе, если оно было успешно отправлено.
    if sent_message and sent_message.message_id:
        await store_message(chat_id, sent_message.message_id, status_message, 'bot')
        await register_message_type(chat_id, sent_message.message_id, 'account_status', bot)

        # Удаление сообщения пользователя после обработки.
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя {message.message_id}: {e}")

    # Удаляем неважные сообщения.
    await delete_unimportant_messages(chat_id, bot)


async def generate_status_message(chat_id: int) -> tuple:
    """
    Генерирует текст сообщения о статусе пользователя и клавиатуру для отправки.

    Параметры:
    - user_id: идентификатор пользователя (целое число).
    - chat_id: идентификатор чата (целое число).
    - bot: объект бота для взаимодействия с Telegram API.

    Возвращает:
    - status_message: сгенерированный текст сообщения.
    - keyboard: клавиатура с кнопкой оплаты, если применимо.
    """
    #################################################################################


    us = await UserCl.load_user(chat_id)

    # if us.servers:
    #     await us.servers[0].delete()
    # else:
    #     print("Список серверов пуст. Нечего удалять.")

    # print("count_key = ", us.count_key)
    new_server = {
        "name_protocol": "wire_guard",
        "name_server": "My server test",
        "country_server": "22222",
        "server_ip": "195.133.14.202",
        "user_ip": "10.8.0.3",
        "name_conf": "test",
        "enable": False,
        "vpn_usage_start_date": "2024-10-26 19:43:52",  # TIMESTAMP placeholder
        "traffic_up": 0,
        "traffic_down": 0,
        "has_paid_key": 1,
        "status_key": "free_key",  # new_user, key_free, waiting_pending, blocked, active
        "is_notification": False,
        "days_after_pay": 30,  # TIMESTAMP placeholder
        "date_payment_key": "2024-10-26 19:43:52",
        "date_expire_of_paid_key": "2024-10-26 19:43:52",
        "date_expire_free_trial": "2024-10-26 19:43:52",
        "url_vless": ""
    }
    await us.add_server(new_server)


    #################################################################################
    #await us.count_key.set(6)
    # await us.user_name.set("TOL")
    #
    # await us.registration_date.set()
    # await us.user_name.set("TOL")
    # await us.user_name.set("TOL")


    # await us.servers[2].user_ip.set("127.127.127.127")
    # await us.servers[0].change_enable(True)

    print("NAME ", us.user_name.get(), "----------------------------------------------------")
    await us.count_key.set(1)
    print("count_key ", us.count_key.get())


    # status_key = await us.servers[0].status_key.get()
    status_key = 0

    # Проверяем, что данные пользователя успешно получены и содержат 4 элемента.
    #if us.count_key.get() > 0:
    if status_key > 0:

        # Определяем текст статуса подписки и создаем клавиатуру в зависимости от статуса.
        if status_key == "waiting_pending":
            str_count_days = "подписка закончена"
            status_sub_txt = "Ожидание оплаты подписки"
            keyboard = create_payment_button(chat_id)
        elif status_key == "new_user":
            days = us.days_since_registration.get()

            if 14 - days < 0:
                str_count_days = 0
            else:
                str_count_days = 14 - days
            status_sub_txt = "Пробный период"
            keyboard = create_payment_button(chat_id)
        elif status_key == "active":
            str_count_days = "активна на месяц"
            status_sub_txt = "Подписка активна на месяц"

            keyboard = create_payment_button(chat_id)

        else:
            # Для любого другого статуса используем его напрямую.
            status_sub_txt = status_key
            keyboard = create_payment_button(chat_id)

        # Формируем текст сообщения о статусе пользователя.
        status_message = (
            f"🕒 Вы с нами уже {us.days_since_registration.get()} дней! 🚀 Какой прогресс! 😎\n"
            f"Действие тарифа: {us.servers[0].days_after_pay.get()}\n"
            f"Имя пользователя: {us.user_name.get()}\n"
            f"Статус подписки: *{status_sub_txt}*"
        )
    else:
        # Если данные пользователя не найдены, отправляем сообщение об ошибке.
        status_message = "Ваши данные не найдены в системе. Обратитесь в поддержку, мы на связи."
        keyboard = None  # В случае ошибки клавиатура не требуется.

    return status_message, keyboard
