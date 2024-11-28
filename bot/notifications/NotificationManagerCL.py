import asyncio
from datetime import datetime
from typing import List, Dict
from bot.notifications.NotificationBaseCL import NotificationBase

class NotificationManager:
    def __init__(self):
        self.notifications: List[NotificationBase] = []
        self.running_notifications = set()  # Множество активных уведомлений для предотвращения дублирования
        self.notification_map: Dict[str, NotificationBase] = {}  # Карта уведомлений по их имени класса

    def register_notification(self, notification: NotificationBase):
        """
        Регистрирует новое уведомление.
        """
        self.notifications.append(notification)
        self.notification_map[notification.__class__.__name__] = notification

    async def run_all_notifications(self, bot):
        """
        Запускает все зарегистрированные уведомления.
        """
        print("Запуск всех уведомлений...")
        for notification in self.notifications:
            await self._run_notification_safe(notification, bot)

    async def run_notifications_by_schedule(self, bot, schedule: dict):
        """
        Запускает уведомления по расписанию.
        schedule: dict - словарь, где ключ - время запуска (HH:MM),
                         значение - список типов уведомлений.
        """
        print("Запуск уведомлений по расписанию...")
        while True:
            try:
                now = datetime.now().strftime("%H:%M")  # Текущее время в формате HH:MM
                if now in schedule:
                    notifications_to_run = schedule[now]
                    for notification_type in notifications_to_run:
                        if notification_type in self.notification_map:
                            await self.run_notification_by_type(notification_type, bot)
                        else:
                            print(f"Уведомление с типом '{notification_type}' не зарегистрировано.")
                await asyncio.sleep(60)  # Проверяем время каждую минуту
            except Exception as e:
                print(f"Ошибка в планировщике уведомлений: {e}")

    async def run_notification_by_type(self, notification_type: str, bot):
        """
        Запускает уведомление по его имени класса.
        notification_type: str - имя класса уведомления.
        """
        if notification_type not in self.notification_map:
            raise ValueError(f"Уведомление с типом '{notification_type}' не найдено.")
        notification = self.notification_map[notification_type]
        await self._run_notification_safe(notification, bot)

    async def _run_notification_safe(self, notification: NotificationBase, bot):
        """
        Безопасный запуск уведомления, предотвращающий дублирование.
        """
        if notification.__class__.__name__ in self.running_notifications:
            print(f"Уведомление {notification.__class__.__name__} уже выполняется. Пропускаем.")
            return

        self.running_notifications.add(notification.__class__.__name__)
        try:
            print(f"Запуск уведомления: {notification.__class__.__name__}")
            await notification.run(bot)
        except Exception as e:
            print(f"Ошибка при выполнении {notification.__class__.__name__}: {e}")
        finally:
            self.running_notifications.remove(notification.__class__.__name__)
