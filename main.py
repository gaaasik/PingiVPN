import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
from aiogram import Bot
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from bot.admin_func.another_settings import another_settings

from bot.admin_func.class_friends import handler_friends
from bot.admin_func.history_key import history_key
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
from bot.handlers.all_menu import main_menu, menu_buy_vpn, menu_device, menu_my_keys, menu_help, \
    menu_share, menu_connect_vpn, menu_payment, menu_about_pingi, menu_subscriptoin_check, keenetic_setup, feedback_menu
from bot.handlers import start, support, \
    user_help_request, feedback, app_downloaded,file_or_qr,thank_you

from bot.admin_func import bonus_days, service_mode,show_statistics,set_on_off
from bot.admin_func.searh_user import search_user_handlers,search_user_by_nickname,search_by_fullname
from bot.admin_func.change_value_key import change_value_key_handler
from bot.payments2.payments_handler_redis import listen_to_redis_queue


from bot.notification_users import notification_migrate_from_wg
from bot.utils.cache import cache_media
from bot.utils.logger import setup_logger
from bot.database.db import database_path_local  #,  init_db
from bot.database.init_db import init_db, update_database
from bot.midlewares.throttling import ThrottlingMiddleware
from bot_instance import BOT_TOKEN, dp, bot
from communication_with_servers.result_processor.start_processor_result_queue import process_queue_results_task
from communication_with_servers.send_type_task import send_creating_user_tasks_for_servers

from models.country_server_data import load_server_data

from models.daily_task_class.DailyTaskManager import DailyTaskManager
from models.notifications.AccessExpiredReminder import AccessExpiredReminder
from models.notifications.CompensationNotificationCL import CompensationNotification
from models.notifications.NotificationManagerCL import NotificationManager
from models.notifications.UnsubscribedNotificationCL import UnsubscribedNotification
from models.notifications.TrialEndingNotificationCL import TrialEndingNotification
from models.notifications.NotificationSchedulerCL import NotificationScheduler
from models.notifications.PaymentReminderCL import PaymentReminder
from models.notifications.WithoutKeyNotification import WithoutKeyNotification
from models.notifications.utils import lottery
import communication_with_servers.result_processor.all_processor.result_creating_user as result_module

from pytz import timezone
moscow = timezone("Europe/Moscow")

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
    manager = DailyTaskManager(bot)
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

        # Ожидаем до целевого времени 217.25.91.109
        await asyncio.sleep(wait_time)

        # Выполняем задачи
        try:
            await manager.execute_daily_tasks()
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
        await asyncio.sleep(time_to_sleep)

        try:
            # Отправляем резервную копию
            await send_backup_db_to_admin(bot)
        except Exception as e:
            # Логирование ошибки и отправка уведомления администратору
            logging.error(f"Ошибка при отправке бекапа базы данных: {e}")
            await send_admin_log(bot, f"Ошибка при отправке бекапа базы данных: {e}")

async def job_wrapper():
    result_module.daily_created_users_wg = 0
    result_module.daily_created_users_vless = 0
    logging.info("🔁 Обнулены суточные счётчики пользователей (WG и VLESS)")

    # ⏩ Запуск создания пользователей
    #await send_creating_user_tasks_for_servers()


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


     #Толян загружает данные из country_server в country_server_data   При отправки создания пользоваетелей неизвестен протокол с которым работает сервер
    country_server_path = os.getenv('country_server_path')
    await load_server_data(country_server_path)
    # Планировщик задач от Толяна
    scheduler = AsyncIOScheduler()
    # ПН (mon), СР (wed), ПТ (fri) в 02:00
    scheduler.add_job(
        job_wrapper,
        CronTrigger(day_of_week="tue,fri", hour=3, minute=0, timezone=moscow)
    )
    scheduler.start()


    await init_db(db_path)
    await update_database(db_path)



    async def run_test():
        # Создаём экземпляр PaymentReminder
        reminder = PaymentReminder()

        # Вызываем метод
        blocked_users = await reminder.fetch_target_users()

        # Выводим результаты
        print(f"Заблокированные пользователи: {len(blocked_users)}")

    #await run_test()
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
    notification_manager.register_notification(CompensationNotification())
    notification_manager.register_notification(AccessExpiredReminder())
    notification_manager.register_notification(WithoutKeyNotification())
    # Инициализация планировщика уведомлений
    notification_scheduler = NotificationScheduler(notification_manager)

    # Настройка расписания уведомлений Ежедневная статистика
    #notification_scheduler.add_to_schedule("11:00", "CompensationNotification")
    notification_scheduler.add_to_schedule("12:00", "UnsubscribedNotification")
    notification_scheduler.add_to_schedule("12:30", "TrialEndingNotification")
    notification_scheduler.add_to_schedule("13:00", "PaymentReminder")  # Добавили PaymentReminder
    notification_scheduler.add_to_schedule("13:30", "AccessExpiredReminder")
    notification_scheduler.add_to_schedule("14:00", "WithoutKeyNotification")
    #пропущенный пользователь

    # us= await UserCl.load_user(763159433)

    # reminder = AccessExpiredReminder()
    # await reminder.send_all_templates_to_admins(bot)

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
    dp.include_router(thank_you.router)
    dp.include_router(show_statistics.router)
    dp.include_router(menu_subscriptoin_check.router)
    dp.include_router(another_settings.router)
    dp.include_router(search_user_handlers.router)
    dp.include_router(set_on_off.router)
    dp.include_router(search_user_by_nickname.router)
    dp.include_router(search_by_fullname.router)
    dp.include_router(service_mode.router)
    dp.include_router(history_key.router)    # history_key
    dp.include_router(bonus_days.router)
    dp.include_router(change_value_key_handler.router)
    dp.include_router(keenetic_setup.router)
    dp.include_router(handler_friends.router)
    dp.include_router(lottery.router)
    dp.include_router(feedback_menu.router)

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
