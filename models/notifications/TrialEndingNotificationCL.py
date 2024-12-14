import asyncio
import os
from datetime import datetime, timedelta
from bot_instance import bot
from models.UserCl import UserCl
from .NotificationBaseCL import NotificationBase
from typing import List
import logging
import json
import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.handlers.admin import send_admin_log
from .PaymentReminderCL import SEREVERS_IP


async def filter_users_with_expired_trials(batch: List[int]) -> List[int]:
    """
    Фильтрует пользователей, у которых пробный период заканчивается через 1-2 дня,
    и проверяет, что уведомление `payment_reminder` ещё не отправлялось.
    """
    expiring_users = []

    async def check_user(chat_id: int):
        try:
            user = await UserCl.load_user(chat_id)
            if not user or not user.servers:
                logging.info(f"Пользователь {chat_id} пропущен: отсутствуют данные пользователя или серверы.")
                return None

            for server in user.servers:
                date_key_off = await server.date_key_off.get()
                has_paid_key = await server.has_paid_key.get()
                is_enabled = await server.enable.get()
                server_ip = await server.server_ip.get()
                # Логируем параметры пользователя
                logging.info(
                    f"Пользователь {chat_id}: date_key_off={date_key_off}, has_paid_key={has_paid_key}, is_enabled={is_enabled}"
                )

                # Проверяем, заканчивается ли пробный период
                if (
                        await is_trial_ending_soon(date_key_off)
                        and has_paid_key == 0
                ):
                    logging.info(f"Пользователь {chat_id} добавлен в список для уведомления.")
                    return chat_id

                # Пропускаем, если сервер уже отключен
                if not is_enabled:
                    logging.info(f"Пользователь {chat_id} пропущен: server.enable=False.")
                    return None

                # Пропускаем, если IP сервера не входит в список
                if server_ip not in SEREVERS_IP:
                    logging.info(f"Пользователь {chat_id} пропущен: server_ip={server_ip} не в списке разрешённых IP.")
                    return None



            logging.info(f"Пользователь {chat_id} пропущен: условия уведомления не выполнены.")
            return None
        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя {chat_id}: {e}")
            return None

    # Параллельная проверка всех пользователей в батче
    results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
    expiring_users = [chat_id for chat_id in results if chat_id is not None]
    return expiring_users
async def is_trial_ending_soon(date_key_off: str) -> bool:
    """
    Проверяет, подходит ли дата окончания пробного периода для отправки уведомления.
    Уведомление отправляется, если дата окончания в пределах от сегодняшнего дня до трех дней вперед.

    :param date_key_off: Строка с датой окончания в формате "%d.%m.%Y %H:%M:%S".
    :return: True, если нужно отправить уведомление, иначе False.
    """
    try:
        today = datetime.now().date()  # Текущая дата
        trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S").date()

        # Проверяем, находится ли дата окончания в пределах от сегодня до +3 дней
        if today <= trial_end_date <= (today + timedelta(days=3)):
            logging.info(
                f"Дата окончания {trial_end_date} в пределах от {today} до {today + timedelta(days=3)}. Уведомление требуется."
            )
            return True
        else:
            logging.info(
                f"Дата окончания {trial_end_date} вне диапазона от {today} до {today + timedelta(days=3)}. Уведомление не требуется."
            )
            return False
    except Exception as e:
        logging.error(f"Ошибка в is_trial_ending_soon: {e}")
        return False



class TrialEndingNotification(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых пробный период заканчивается через 1-2 дня.
        """
        try:
            all_users = await UserCl.get_all_users()
            expiring_users = []

            # Разделяем пользователей на батчи и фильтруем
            for batch in self.split_into_batches(all_users):
                expiring_users.extend(await filter_users_with_expired_trials(batch))

            async def fetch_target_users(self) -> List[int]:
                """
                Получение пользователей, у которых пробный период заканчивается через 1-2 дня.
                """
                try:
                    all_users = await UserCl.get_all_users()
                    expiring_users = []

                    # Разделяем пользователей на батчи и фильтруем
                    for batch in self.split_into_batches(all_users):
                        expiring_users.extend(await filter_users_with_expired_trials(batch))

                    # Логируем количество пользователей
                    if expiring_users:
                        safe_message = (
                            f"\ud83d\udd14 {len(expiring_users)} пользователей нуждаются в уведомлении о завершении пробного периода.\n всего пользователей {len(all_users)}"
                        ).encode('utf-8', 'replace').decode('utf-8')
                        await send_admin_log(bot, safe_message)
                    else:
                        safe_message = "\ud83d\udd14 Нет пользователей для уведомления о завершении пробного периода."
                        await send_admin_log(bot, safe_message.encode('utf-8', 'replace').decode('utf-8'))

                    return expiring_users
                except Exception as e:
                    logging.error(f"Ошибка при выборке пользователей: {e}")
                    return []

            return expiring_users
        except Exception as e:
            logging.error(f"Ошибка при выборке пользователей: {e}")
            return []

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о завершении пробного периода.
        """
        return (
            "\u23f3 <b>Осталось совсем чуть чуть!</b> \ud83d\udc27\n\n"
            "\ud83d\udd10 <b>Продлите доступ к VPN прямо сейчас!</b>\n\n"
            "\ud83e\udd76 <b>Ваш пробный период скоро завершится.</b> Чтобы продолжить пользоваться нашим надёжным VPN:\n"
            "\ud83d\udcb3 Оформите подписку и наслаждайтесь безопасным и быстрым соединением.\n\n"
            "\ud83c\udfaf <b>Почему стоит остаться с нами?</b>\n"
            "\u2705 Высокая скорость\n"
            "\u2705 Полная анонимность\n"
            "\u2705 Без рекламы\n\n"
            "\ud83d\udc65 <b>Хотите продлить доступ бесплатно?</b>\n"
            "Пригласите друга и получите <b>+3 дня</b>.\n"
            "Если ваш друг оформит подписку, вы получите <b>+14 дней</b> в подарок! \ud83c\udf81"
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Возвращает клавиатуру с кнопками для оплаты.
        """
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="\ud83d\udcb3 Оплатить ключ", callback_data="buy_vpn")],
                [InlineKeyboardButton(text="\ud83d\udd17 Поделиться c другом", callback_data="show_referral_link")],
                [InlineKeyboardButton(text="\ud83c\udfe0 Главное меню", callback_data="main_menu")]
            ]
        )
        return keyboard

    async def after_send_success(self, user_id: int):
        """
        Действия после успешной отправки уведомления:
        Запись логов об отправке уведомления в базу данных.
        """
        today = datetime.now().strftime("%m_%d")  # Формат мм_дд
        notification_type = f"notification_{today}"

        try:
            user = await UserCl.load_user(user_id)

            if not user:
                logging.error(f"Пользователь {user_id} не найден для обновления статуса.")
                return

            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent",
                    "message_type": "trial_ending"
                }

                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()

            logging.info(f"Уведомление успешно отправлено и логировано для пользователя {user_id}.")

        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя {user_id} в after_send_success: {e}")
