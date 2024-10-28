#2:28

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
from bot.payments2.payments_handler_redis import listen_to_redis_queue
#from bot.payments2.payments_handler_redis import listen_to_redis_queue
from bot.database.db import add_user  #, check_24_hour_db
from bot.handlers import start, status, support, share, start_to_connect, instructions, \
    device_choice, app_downloaded, file_or_qr, subscription, speedtest, user_help_request, feedback
from bot.payments2 import payments_handler_redis
from bot.utils.cache import cache_media
from bot.utils.check_status import check_db  #, notify_users_with_free_status
from bot.utils.logger import setup_logger
from bot.database.db import init_db, database_path_local
from bot.midlewares.throttling import ThrottlingMiddleware
from bot_instance import BOT_TOKEN, dp, bot
from flask_app.all_utils_flask_db import initialize_db

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
    await asyncio.sleep(10800)
    while True:
        await send_admin_log(bot, "Пинг бота - прошло 3 час работы бота.")

        # Пример асинхронного вызова
        # await notify_users_with_free_status(bot)
        await asyncio.sleep(10800)


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
            await check_db(bot)

            # Уведомление об успешном завершении
            await send_admin_log(bot, "Обновление базы данных прошло успешно.")

        except Exception as e:
            # Логирование ошибки и отправка уведомления администратору
            logging.error(f"Ошибка при выполнении обновления базы данных: {e}")
            await send_admin_log(bot, f"Обновление базы данных завершилось с ошибкой: {e}")

        # Мы не ждем фиксированное количество времени, а снова пересчитываем время до следующего 3:00


async def main():
    try:
        await send_admin_log(bot, "Бот запустился")
        # Настраиваем логирование
        setup_logger("logs/bot.log")
    except Exception as e:
        logging.exception(f"Неверное логирование: Ошибка при отправке запуске очереди Redis: {e}")

    await on_startup()
    await initialize_db()

    # Пример использования:
    #add_column_to_payments("new_column_name")

    # Читаем токен бота из переменной окружения
    if not BOT_TOKEN:
        print("Ошибка: Токен не найден в .env файле!")
        return
    print(f"Токен успешно загружен: {BOT_TOKEN}")

    # Указываем путь к базе данных
    db_path = Path(os.getenv('database_path_local'))
    if not db_path.exists():
        print("Файл базы данных не найден!")
        return
    print(f"Путь к базе данных: {db_path}")
    # Инициализация бота и диспетчера

    # Инициализация базы данных SQLite
    await init_db(db_path)
    # Запускаем асинхронную задачу для периодической отправки сообщений админу
    asyncio.create_task(periodic_task(bot))
    #asyncio.create_task(periodic_task_24_hour(bot))
    asyncio.create_task(listen_to_redis_queue(bot))  # 1 час
    asyncio.create_task(periodic_backup_task(bot))
    # Промежуточное ПО для предотвращения спама
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1))

    # Регистрация хэндлеров
    dp.include_router(start.router)
    dp.include_router(speedtest.router)
    dp.include_router(status.router)
    dp.include_router(support.router)
    #dp.include_router(admin.router)
    dp.include_router(share.router)
    dp.include_router(start_to_connect.router)
    dp.include_router(instructions.router)
    dp.include_router(device_choice.router)
    dp.include_router(app_downloaded.router)
    dp.include_router(file_or_qr.router)
    dp.include_router(subscription.router)
    dp.include_router(user_help_request.router)
    dp.include_router(payments_handler_redis.router)
    dp.include_router(feedback.router)
    #dp.include_router(payment.router)

    # Запуск бота
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(f"Произошла ошибка: {e}")
    finally:
        await send_admin_log(bot, "Бот завершил работу и пошел отдыхать")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
