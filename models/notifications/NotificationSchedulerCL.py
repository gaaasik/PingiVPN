import asyncio
import logging
from datetime import datetime, timedelta

from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS


class NotificationScheduler:
    def __init__(self, notification_manager):
        """
        Планировщик уведомлений.
        """
        self.notification_manager = notification_manager
        self.schedule = {}

    def add_to_schedule(self, time: str, notification_type: str):
        """
        Добавляет уведомление в расписание.
        :param time: Время в формате HH:MM.
        :param notification_type: Имя класса уведомления.
        """
        if time not in self.schedule:
            self.schedule[time] = []
        self.schedule[time].append(notification_type)

    async def start(self, bot):
        logging.info("Планировщик уведомлений запущен.")
        while True:
            now = datetime.now()
            next_time, notifications = self.get_next_notification(now)

            if next_time is None:
                logging.info("Нет уведомлений в расписании.")
                await asyncio.sleep(60)  # Спим 1 час, если расписание пусто
                continue

            time_to_sleep = (next_time - now).total_seconds()

            logging.info(f"Следующее уведомление {notifications} через {time_to_sleep / 60:.2f} минут.")

            # Засыпаем до времени выполнения
            await asyncio.sleep(time_to_sleep)

            for notification_type in notifications:
                logging.info(f"Запуск уведомления {notification_type} в {next_time.strftime('%H:%M')}")

                # Уведомляем администраторов об отправке
                try:
                    await send_admin_log(bot, f"Запуск уведомления {notification_type}.")
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления администратору: {e}")

                try:
                    await self.notification_manager.run_notification_by_type(notification_type, bot)
                except Exception as e:
                    logging.error(f"Ошибка при выполнении уведомления {notification_type}: {e}")

    def get_next_notification(self, now: datetime):
        """
        Рассчитывает ближайшее время уведомления.
        :param now: Текущий момент времени.
        :return: Кортеж (datetime, список уведомлений).
        """
        closest_time = None
        closest_notifications = []

        for time_str, notifications in self.schedule.items():
            scheduled_time = datetime.strptime(time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )

            # Если время уведомления уже прошло сегодня, переносим на завтра
            if scheduled_time < now:
                scheduled_time += timedelta(days=1)

            # Ищем ближайшее время
            if closest_time is None or scheduled_time < closest_time:
                closest_time = scheduled_time
                closest_notifications = notifications

        return closest_time, closest_notifications
