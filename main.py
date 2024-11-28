import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
from bot.handlers.all_menu import main_menu, menu_buy_vpn, menu_device, menu_my_keys, menu_help, \
    menu_share, menu_connect_vpn, menu_payment, menu_about_pingi, menu_subscriptoin_check
from bot.notification_users.notification_migrate_from_wg import send_initial_update_notification, \
    send_choice_notification, get_stay_on_wg_count
from bot.notification_users.request_payment import process_notifications_request_payment

from bot.payments2.payments_handler_redis import listen_to_redis_queue
#from bot.payments2.payments_handler_redis import listen_to_redis_queue
from bot.handlers import start, support, \
    user_help_request, feedback, app_downloaded,file_or_qr
from bot.notification_users import notification_migrate_from_wg
from bot.utils.cache import cache_media
#from bot.utils.check_status import check_db  #, notify_users_with_free_status
from bot.utils.logger import setup_logger
from bot.database.db import database_path_local  #,  init_db
from bot.database.init_db import init_db
from bot.midlewares.throttling import ThrottlingMiddleware
from bot_instance import BOT_TOKEN, dp, bot
from communication_3x_ui.send_json import process_task_queue
#from fastapi_app.all_utils_flask_db import initialize_db
from models.UserCl import UserCl

from bot.notifications.NotificationManagerCL import NotificationManager
from bot.notifications.UnsubscribedNotificationCL import  UnsubscribedNotification
from bot.notifications.PaymentReminderCL import PaymentReminder
from bot.notifications.TrialEndingNotificationCL import TrialEndingNotification
from bot.notifications.NotificationSchedulerCL import NotificationScheduler
# Загружаем переменные окружения из файла .env
load_dotenv()

# Глобальная переменная для хранения экземпляра бота

PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
video_path = os.getenv("video_path")
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')


async def on_startup():
    """Кэширование изображений при старте"""
    image_path = os.path.join(PATH_TO_IMAGES, "Hello.png")
    print('закешировали приветственное фото')
    await cache_media(image_path, video_path)


# Функция, которая выполняется каждые 10 секунд
async def periodic_task(bot: Bot):

    # Ждем 10 секунд после старта бота
    await asyncio.sleep(86400)
    while True:
        #await notify_users_about_protocol_change(bot)

        count_stay_on_wg = await get_stay_on_wg_count()
        report_text = (
            f"📊 *Ежедневный отчет*\n\n"
            f"{count_stay_on_wg} пользователей нажали 'Остаться на WireGuard' сегодня.\n"
            "Рекомендуем поддержать их в переходе на VLESS."
        )
        await send_admin_log(bot, report_text)

        # Пример асинхронного вызова
        # await notify_users_with_free_status(bot)
        await asyncio.sleep(86400)


async def send_backup_db_to_admin(bot: Bot):
    # Проверка, существует ли файл базы данных
    if not os.path.exists(database_path_local):
        print(f"Ошибка: Файл базы данных не найден по пути {database_path_local}")
        return

    # Формируем текст сообщения с текущей датой
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caption = f"Резервная копия базы данных за {current_date}"

    try:
        # Открываем файл базы данных
        backup_file = FSInputFile(database_path_local)

        # Отправляем файл каждому администратору из списка
        for admin_chat_id in ADMIN_CHAT_IDS:
            print(f"Отправка резервной копии в чат {admin_chat_id}.")
            await bot.send_document(chat_id=admin_chat_id, document=backup_file, caption=caption)

        print("Резервная копия успешно отправлена.")
    except Exception as e:
        print(f"Ошибка при отправке резервной копии: {e}")


async def periodic_backup_task(bot: Bot):
    while True:
        # Текущее время
        now = datetime.now()

        # Время следующего 3:00 ночи
        next_3am = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=15, minutes=7)

        # Если сейчас уже после 3:00 ночи, то следующий запуск будет завтра в 3:00
        if now > next_3am:
            next_3am += timedelta(days=1)

        # Рассчитываем, сколько времени осталось до следующего 3:00
        time_to_sleep = (next_3am - now).total_seconds()

        # Спим до следующего 3:00
        print(f"Следующая отправка бд в чат телеграма в {next_3am}, ждем {time_to_sleep} секунд.")
        await asyncio.sleep(time_to_sleep)

        try:
            # Отправляем резервную копию
            await send_backup_db_to_admin(bot)
        except Exception as e:
            # Логирование ошибки и отправка уведомления администратору
            logging.error(f"Ошибка при отправке бекапа базы данных: {e}")
            await send_admin_log(bot, f"Ошибка при отправке бекапа базы данных: {e}")


async def periodic_task_24_hour(bot: Bot):
    # Ждем 1 секунду после старта бота (как у тебя)
    await asyncio.sleep(1)

    while True:
        # Текущее время
        now = datetime.now()

        # Время следующего 3:00 ночи
        next_3am = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=15, minutes=7)

        # Если сейчас уже после 3:00 ночи, то следующий запуск будет завтра в 3:00
        if now > next_3am:
            next_3am += timedelta(days=1)

        # Рассчитываем, сколько времени осталось до следующего 3:00
        time_to_sleep = (next_3am - now).total_seconds()

        # Спим до следующего 3:00
        print(f"Следующее выполнение в {next_3am}, ждем {time_to_sleep} секунд.")
        await asyncio.sleep(time_to_sleep)

        # Когда просыпаемся, выполняем задачу
        print("Сработала функция в 3:00 ночи")
        try:
            # Сообщаем администратору о начале обновления
            await send_admin_log(bot, "Пинг бота - началось обновление базы данных в 3:00.")

            # Выполнение проверки базы данных
            #await check_db(bot)

            # Уведомление об успешном завершении
            await send_admin_log(bot, "Обновление базы данных прошло успешно.")

        except Exception as e:
            # Логирование ошибки и отправка уведомления администратору
            logging.error(f"Ошибка при выполнении обновления базы данных: {e}")
            await send_admin_log(bot, f"Обновление базы данных завершилось с ошибкой: {e}")

        # Мы не ждем фиксированное количество времени, а снова пересчитываем время до следующего 3:00


async def notify_users_about_protocol_change(bot: Bot):
    errors = {}
    all_chat_id = await UserCl.get_all_users()
    # Размер батча (количество пользователей в одном чанке)
    batch_size = 50

    # Функция для разделения списка пользователей на чанки
    def chunk_list(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    # Обрабатываем чанки пользователей
    for chunk in chunk_list(all_chat_id, batch_size):
        # Отправляем уведомления всем пользователям в текущем чанке одновременно
        await asyncio.gather(*[send_initial_update_notification(chat_id, bot, errors) for chat_id in chunk])

    # Логируем количество ошибок после обработки батча
    await send_admin_log(bot, f"При уведомлении возникло {len(errors)} ошибок на текущий момент.")



async def main():
    """Главная функция запуска"""
    try:
        await send_admin_log(bot, "Бот запустился")
        setup_logger("logs/bot.log")
    except Exception as e:
        logging.exception(f"Ошибка при настройке логирования: {e}")

    await on_startup()

    if not BOT_TOKEN:
        print("Ошибка: токен бота не найден в .env файле!")
        return

    db_path = os.getenv('database_path_local')
    if not db_path or not Path(db_path).exists():
        print(f"Ошибка: файл базы данных {db_path} не найден!")
        return
    print(f"Путь к базе данных: {db_path}")

    await init_db(db_path)

    asyncio.create_task(periodic_task(bot))
    asyncio.create_task(listen_to_redis_queue(bot))
    asyncio.create_task(periodic_backup_task(bot))
    asyncio.create_task(process_task_queue())

    # Инициализация менеджера уведомлений
    notification_manager = NotificationManager()

    # Регистрация уведомлений
    notification_manager.register_notification(
        UnsubscribedNotification(channel_username="pingi_hub")
    )

    # Инициализация планировщика уведомлений
    notification_scheduler = NotificationScheduler(notification_manager)

    # Настройка расписания уведомлений
    notification_scheduler.add_to_schedule("12:00", "UnsubscribedNotification")

    # Запуск уведомлений по расписанию
    asyncio.create_task(notification_scheduler.start(bot))

    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))
    dp.include_router(start.router)
    dp.include_router(support.router)
    dp.include_router(menu_about_pingi.router)
    dp.include_router(user_help_request.router)
    dp.include_router(menu_payment.router)
    dp.include_router(feedback.router)
    dp.include_router(main_menu.router)
    dp.include_router(menu_buy_vpn.router)
    dp.include_router(menu_share.router)
    dp.include_router(menu_help.router)
    dp.include_router(menu_device.router)
    dp.include_router(menu_connect_vpn.router)
    dp.include_router(menu_my_keys.router)
    dp.include_router(notification_migrate_from_wg.router)
    dp.include_router(app_downloaded.router)
    dp.include_router(file_or_qr.router)

    dp.include_router(menu_subscriptoin_check.router)

    try:
        pass
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
    except KeyboardInterrupt:
        print("Работа прервана пользователем")
    finally:
        await send_admin_log(bot, "Бот завершил работу и пошел отдыхать")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Завершение работы...")
