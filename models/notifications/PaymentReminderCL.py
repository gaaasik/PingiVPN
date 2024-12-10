import asyncio
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.UserCl import UserCl
from models.notifications.NotificationBaseCL import NotificationBase
from models.notifications.utils.dates import is_trial_ended
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS  # Функция отправки сообщения админу
from bot_instance import bot  # Инстанс бота для отправки сообщений
import datetime

class PaymentReminder(NotificationBase):
    async def filter_users_with_unpaid_access(self, batch: List[int]) -> List[int]:
        """
        Фильтрует пользователей, чей пробный период завершился и подписка не оплачена.
        """
        blocked_users = []

        async def check_user(chat_id: int):
            try:
                user = await UserCl.load_user(chat_id)
                if not user or not user.servers:
                    return None

                for server in user.servers:
                    date_key_off = await server.date_key_off.get()
                    has_paid_key = await server.has_paid_key.get()
                    ip = await server.server_ip.get()

                    # Проверяем, завершился ли пробный период и не оплачена ли подписка
                    if await is_trial_ended(date_key_off) and has_paid_key == 0 and ip == "90.156.228.68" :
                        return chat_id
            except Exception as e:
                print(f"Ошибка при обработке пользователя {chat_id}: {e}")
                return None

        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
        blocked_users = [chat_id for chat_id in results if chat_id is not None]
        print(blocked_users)
        return blocked_users

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых завершён пробный период и требуется оплата.
        """
        all_users = await UserCl.get_all_users()
        blocked_users = []
        for batch in self.split_into_batches(all_users):
            blocked_users.extend(await self.filter_users_with_unpaid_access(batch))

        # Логирование количества заблокированных пользователей
        try:
            if blocked_users:
                await send_admin_log(bot, f"🔔 {len(blocked_users)} пользователей нуждаются в уведомлении об оплате.")
            else:
                await send_admin_log(bot, "🔔 Нет пользователей для уведомления о блокировке доступа.")
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу: {e}")

        return blocked_users

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о блокировке доступа.
        """
        return (
            "❌ <b>Ваш доступ заблокирован</b>.\n\n"
            "Пробный период завершён. Для продолжения использования VPN, пожалуйста, оформите подписку:\n\n"
            "💳 <b>Оплатите доступ</b> и наслаждайтесь безопасным соединением без ограничений."
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Клавиатура для сообщения об оплате.
        """
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="buy_vpn")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
        return keyboard

    async def after_send_success(self, user_id: int):
        """
        Действия после успешной отправки уведомления:
        1. Смена статуса пользователя, если пробный период истёк.
        2. Обновление логов.
        """
        try:
            if user_id in ADMIN_CHAT_IDS:

                user = await UserCl.load_user(user_id)
                for server in user.servers:

                    date_key_off = await server.date_key_off.get()

                    # Если дата окончания истекла, блокируем доступ
                    if datetime.datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S") < datetime.datetime.now():
                        await server.enable.set(False)

                print(f"Уведомление успешно отправлено пользователю {user_id}.")

        except Exception as e:
            print(f"Ошибка при обновлении статуса пользователя {user_id}: {e}")
