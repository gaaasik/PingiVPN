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
from bot.notification_users.notification_migrate_from_wg import get_stay_on_wg_count

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
from communication_with_servers.queue_results_task import process_queue_results_task
from models.ServerCl import load_server_data
#from communication_with_servers.send_json import process_task_queue
# from communication_with_servers.send_json import process_task_queue
#from fastapi_app.all_utils_flask_db import initialize_db
from models.UserCl import UserCl
from models.daily_task_class.DailyTaskManager import DailyTaskManager
#from fastapi_app.all_utils_flask_db import initialize_db

from models.notifications.NotificationManagerCL import NotificationManager
from models.notifications.UnsubscribedNotificationCL import  UnsubscribedNotification
from models.notifications.TrialEndingNotificationCL import TrialEndingNotification
from models.notifications.NotificationSchedulerCL import NotificationScheduler
from models.notifications.PaymentReminderCL import PaymentReminder

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


async def schedule_daily_tasks(bot):
    """
    Планировщик для запуска ежедневных задач в 10 утра.
    """
    #manager = DailyTaskManager(bot)
    #await manager.execute_daily_tasks()
    while True:
        now = datetime.now()
        target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)

        # Если текущее время уже позже 10 утра, планируем на следующий день
        if now > target_time:
            target_time += timedelta(days=1)

        # Рассчитываем, сколько времени осталось до запуска
        wait_time = (target_time - now).total_seconds()
        print(f"Следующая задача будет выполнена через {wait_time} секунд")

        # Ожидаем до целевого времени
        await asyncio.sleep(wait_time)

        # Выполняем задачи
        try:
            pass
            #await manager.execute_daily_tasks()
        except Exception as e:
            print(f"Ошибка при выполнении ежедневных задач: {e}")


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




# async def notify_users_about_protocol_change(bot: Bot):
#     errors = {}
#     all_chat_id = await UserCl.get_all_users()
#     # Размер батча (количество пользователей в одном чанке)
#     batch_size = 50
#
#     # Функция для разделения списка пользователей на чанки
#     def chunk_list(lst, size):
#         for i in range(0, len(lst), size):
#             yield lst[i:i + size]
#
#     # Обрабатываем чанки пользователей
#     for chunk in chunk_list(all_chat_id, batch_size):
#         # Отправляем уведомления всем пользователям в текущем чанке одновременно
#         await asyncio.gather(*[send_initial_update_notification(chat_id, bot, errors) for chat_id in chunk])
#
#     # Логируем количество ошибок после обработки батча
#     await send_admin_log(bot, f"При уведомлении возникло {len(errors)} ошибок на текущий момент.")



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

    #Толян загружает данные из country_server в country_server_data
    country_server_path = os.getenv('country_server_path')
    await load_server_data(country_server_path)


    # Запуск ежедневных задач
    asyncio.create_task(schedule_daily_tasks(bot))
    asyncio.create_task(listen_to_redis_queue(bot))
    asyncio.create_task(periodic_backup_task(bot))
    asyncio.create_task(process_queue_results_task())

    # Инициализация менеджера уведомлений
    notification_manager = NotificationManager()
    notification_manager.register_notification(
        UnsubscribedNotification(channel_username="pingi_hub")
    )
    notification_manager.register_notification(
        TrialEndingNotification()
    )
    notification_manager.register_notification(
        PaymentReminder()  # Регистрация PaymentReminder
    )

    # Инициализация планировщика уведомлений
    notification_scheduler = NotificationScheduler(notification_manager)

    # Настройка расписания уведомлений
    notification_scheduler.add_to_schedule("12:00", "UnsubscribedNotification")
    notification_scheduler.add_to_schedule("13:00", "TrialEndingNotification")
    notification_scheduler.add_to_schedule("14:00", "PaymentReminder")  # Добавили PaymentReminder

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
