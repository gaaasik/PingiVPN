import aiosqlite
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

class ReferralCl:
    def __init__(self, referral_old_chat_id: int, referral_new_chat_id: int):
        self.referral_old_chat_id = referral_old_chat_id  # ID пригласившего пользователя
        self.referral_new_chat_id = referral_new_chat_id  # ID приглашенного пользователя
        self.date_referred: Optional[str] = None          # Дата создания реферала
        self.referral_status: str = "invited"             # Статус реферала (invited, active, paid)
        self.bonus_status: str = "no_bonus"               # Статус бонуса (no_bonus, bonus_added)
        self.date_bonus_awarded: Optional[str] = None     # Дата начисления бонуса

    @classmethod
    async def create_referral(cls, referral_old_chat_id: int, referral_new_chat_id: int) -> "ReferralCl":
        """
        Создаёт новую запись о реферале в базе данных.
        """
        referral = cls(referral_old_chat_id, referral_new_chat_id)
        referral.date_referred = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = """
        INSERT INTO referrals (
            referral_old_chat_id,
            referral_new_chat_id,
            date_referred,
            referral_status,
            bonus_status
        ) VALUES (?, ?, ?, ?, ?)
        """
        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                await db.execute(query, (
                    referral_old_chat_id,
                    referral_new_chat_id,
                    referral.date_referred,
                    referral.referral_status,
                    referral.bonus_status
                ))
                await db.commit()
                logging.info(f"Реферальная связь создана: {referral_old_chat_id} -> {referral_new_chat_id}")
        except Exception as e:
            logging.error(f"Ошибка при создании реферальной записи: {e}")
            raise

        return referral

    @classmethod
    async def handle_referral(cls, chat_id, referral_old_chat_id, bot):
        """
        Обработка нового реферала. Создает запись в таблице и отправляет сообщение рефереру.
        """
        # Проверяем, существует ли уже пользователь
        from models.UserCl import UserCl
        if await UserCl.user_exists(chat_id):
            logging.info(f"Пользователь {chat_id} уже существует. Реферальная связь не требуется.")
            return

        # Создаем запись о реферале
        referral = await cls.create_referral(referral_old_chat_id, chat_id)

        # Получаем данные о приглашенном пользователе
        new_user = await bot.get_chat(chat_id)
        new_user_name = new_user.username or new_user.full_name
        referral_message = (
            f"🎉 Ура! Пользователь {new_user_name} (@{new_user.username or '—'}) присоединился к Pingi VPN по вашей ссылке."
            "При начале использования сервиса вам будут начислены бонусные дни! 🎁"
        )

        # Отправляем уведомление пригласившему пользователю
        try:
            await bot.send_message(referral_old_chat_id, referral_message)
            logging.info(f"Сообщение отправлено рефереру {referral_old_chat_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения рефереру {referral_old_chat_id}: {e}")

    @classmethod
    async def load_referral(cls, referral_old_chat_id: int, referral_new_chat_id: int) -> Optional["ReferralCl"]:
        """
        Загружает существующий реферал из базы данных.
        """
        query = """
        SELECT referral_old_chat_id, referral_new_chat_id, date_referred, referral_status, bonus_status, date_bonus_awarded
        FROM referrals WHERE referral_old_chat_id = ? AND referral_new_chat_id = ?
        """
        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query, (referral_old_chat_id, referral_new_chat_id)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        self = cls(referral_old_chat_id=row[0], referral_new_chat_id=row[1])
                        self.date_referred = row[2]
                        self.referral_status = row[3]
                        self.bonus_status = row[4]
                        self.date_bonus_awarded = row[5]
                        return self
        except Exception as e:
            logging.error(f"Ошибка при загрузке реферала: {e}")
            raise

        return None

    @classmethod
    async def get_all_referrals(cls) -> List["ReferralCl"]:
        """
        Возвращает список всех рефералов.
        """
        query = "SELECT referral_old_chat_id, referral_new_chat_id FROM referrals"
        referrals = []

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    referrals = [
                        await cls.load_referral(row[0], row[1])
                        for row in rows
                    ]
        except Exception as e:
            logging.error(f"Ошибка при получении всех рефералов: {e}")
            raise

        return referrals

    async def check_activation(self) -> bool:
        """
        Проверяет, активирован ли реферал (если приглашенный пользователь добавил сервер).
        """
        if self.bonus_status in ["bonus_3_days_added", "bonus_14_days_added"]:
            logging.info(f"Бонус за активацию уже начислен для реферала {self.referral_new_chat_id}.")
            return False

        from models.UserCl import UserCl
        user = await UserCl.load_user(self.referral_new_chat_id)
        if not user or not user.servers:
            return False

        self.referral_status = "active"
        await self.update_referral_status()
        await self.add_bonus_days(bonus_days=3, bonus_type="bonus_3_days_added")
        return True

    async def check_payment(self) -> bool:
        """
        Проверяет, оплатил ли приглашенный пользователь подписку.
        """
        if self.bonus_status == "bonus_14_days_added":
            logging.info(f"Бонус за оплату уже начислен для реферала {self.referral_new_chat_id}.")
            return False

        from models.UserCl import UserCl
        user = await UserCl.load_user(self.referral_new_chat_id)
        if not user or not user.servers:
            return False

        for server in user.servers:
            has_paid_key = await server.has_paid_key.get()
            if has_paid_key > 0:  # Если пользователь оплатил хотя бы один ключ
                self.referral_status = "paid"
                await self.update_referral_status()
                await self.add_bonus_days(bonus_days=14, bonus_type="bonus_14_days_added")
                return True

        return False

    async def add_bonus_days(self, bonus_days: int, bonus_type: str):
        """
        Добавляет бонусные дни пользователю, пригласившему реферала.
        """
        from models.UserCl import UserCl
        inviter = await UserCl.load_user(self.referral_old_chat_id)
        if not inviter or not inviter.servers:
            return

        for server in inviter.servers:
            current_date_key_off = await server.date_key_off.get()
            current_date_key_off = datetime.strptime(current_date_key_off, "%d.%m.%Y %H:%M:%S")
            new_date_key_off = current_date_key_off + timedelta(days=bonus_days)
            await server.date_key_off.set(new_date_key_off.strftime("%d.%m.%Y %H:%M:%S"))

        self.bonus_status = bonus_type
        self.date_bonus_awarded = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await self.update_referral_status()

    async def update_referral_status(self):
        """
        Обновляет статус реферала в базе данных.
        """
        query = "UPDATE referrals SET referral_status = ?, bonus_status = ? WHERE referral_old_chat_id = ? AND referral_new_chat_id = ?"
        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                await db.execute(query, (
                    self.referral_status, self.bonus_status,
                    self.referral_old_chat_id, self.referral_new_chat_id
                ))
                await db.commit()
        except Exception as e:
            logging.error(f"Ошибка при обновлении статуса реферала: {e}")
            raise



    async def to_dict(self) -> Dict:
        """
        Преобразует объект реферала в словарь.
        """
        return {
            "referral_old_chat_id": self.referral_old_chat_id,
            "referral_new_chat_id": self.referral_new_chat_id,
            "date_referred": self.date_referred,
            "referral_status": self.referral_status,
            "bonus_status": self.bonus_status,
            "date_bonus_awarded": self.date_bonus_awarded,
        }
