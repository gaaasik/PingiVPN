import json

import aiosqlite
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from bot.handlers.admin import send_admin_log
from bot_instance import bot


class ReferralCl:
    # Возможные статусы реферала
    STATUS_INVITED = "invited"       # Пользователь приглашен, но еще не получил ссылку
    STATUS_ACTIVATED = "activated"   # Пользователь получил ссылку и начал пользоваться
    STATUS_PAID = "paid"             # Пользователь оплатил подписку

    # Возможные статусы бонусов
    BONUS_NONE = "no_bonus"         # Бонус не начислен
    BONUS_ACTIVATION = "bonus_2_days_added"  # Начислены 2 дня за активацию close()
    BONUS_PAYMENT = "bonus_14_days_added"    # Начислены 14 дней за оплату подписки


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
        referral.date_referred = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

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

        # Создаем запись о реферале
        referral = await cls.create_referral(referral_old_chat_id, chat_id)

        # Получаем данные о приглашенном пользователе
        new_user = await bot.get_chat(chat_id)
        new_user_name = new_user.username or new_user.full_name
        referral_message = (
            f"🎉 Спасибо! Пользователь {new_user_name} (@{new_user.username or '—'}) присоединился к Pingi VPN по вашей ссылке 🎁 \n"
            f"🎁 Вам будут начислены бонусные дни !"
        )

        # Отправляем уведомление пригласившему пользователю
        try:
            if referral_old_chat_id !=1021956655:
                await bot.send_message(referral_old_chat_id, referral_message)
            logging.info(f"Сообщение отправлено рефереру {referral_old_chat_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения рефереру {referral_old_chat_id}: {e}")

    @classmethod
    async def get_user_referrals(cls, referral_old_chat_id: int) -> List["ReferralCl"]:
        """
        Получает список всех рефералов, приглашенных пользователем. Для вывода пользователям.
        """
        query = """
        SELECT referral_new_chat_id, date_referred, referral_status, bonus_status
        FROM referrals WHERE referral_old_chat_id = ?
        """
        referrals = []

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query, (referral_old_chat_id,)) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        referral = cls(referral_old_chat_id, row[0])
                        referral.date_referred = row[1]
                        referral.referral_status = row[2]
                        referral.bonus_status = row[3]
                        referrals.append(referral)
        except Exception as e:
            logging.error(f"Ошибка при получении списка рефералов пользователя {referral_old_chat_id}: {e}")

        return referrals

    @classmethod
    async def add_referral_bonus(cls, referral_new_chat_id: int):
        """
        Начисляет бонус пригласившему пользователю:
        - 2 дня за активацию (получение VPN-ссылки).
        """
        query_check = """
        SELECT referral_old_chat_id, referral_status, bonus_status FROM referrals WHERE referral_new_chat_id = ?
        """
        query_update_activation = """
        UPDATE referrals SET referral_status = ?, bonus_status = ? WHERE referral_new_chat_id = ?
        """

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query_check, (referral_new_chat_id,)) as cursor:
                    row = await cursor.fetchone()

                    if not row:
                        return  # Нет реферала - ничего не делаем

                    referral_old_chat_id, referral_status, bonus_status = row

                    if referral_status == cls.STATUS_INVITED:
                        # Первый раз активирует VPN → даем 2 дня бонуса
                        if bonus_status == cls.BONUS_NONE:
                            await cls._add_days_to_inviter(referral_old_chat_id, days=2)

                            # Обновляем статус в БД
                            await db.execute(query_update_activation,
                                             (cls.STATUS_ACTIVATED, cls.BONUS_ACTIVATION, referral_new_chat_id))
                            await db.commit()

                            logging.info(f"Бонус за активацию начислен пользователю {referral_old_chat_id}.")
                            await send_admin_log(bot,f"🎁 Пользователю {referral_old_chat_id} начислено 2 дня после получения ключа !")

        except Exception as e:
            logging.error(f"Ошибка при начислении бонуса за активацию: {e}")

    @classmethod
    async def add_referral_bonus_after_pay(cls, referral_new_chat_id: int, bot):
        """
        Начисляет бонус за оплату подписки (10 дней) пригласившему пользователю.
        Также отправляет уведомление рефереру.
        """
        query_check = """
        SELECT referral_old_chat_id, referral_status, bonus_status FROM referrals WHERE referral_new_chat_id = ?
        """
        query_update_payment = """
        UPDATE referrals SET referral_status = ?, bonus_status = ? WHERE referral_new_chat_id = ?
        """

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query_check, (referral_new_chat_id,)) as cursor:
                    row = await cursor.fetchone()

                    if not row:
                        return  # Нет реферала - ничего не делаем

                    referral_old_chat_id, referral_status, bonus_status = row

                    if referral_status == cls.STATUS_ACTIVATED:
                        # Если бонус за оплату еще не был выдан
                        if bonus_status != cls.BONUS_PAYMENT:
                            await cls._add_days_to_inviter(referral_old_chat_id, days=10)

                            # Обновляем статус в БД
                            await db.execute(query_update_payment,
                                             (cls.STATUS_PAID, cls.BONUS_PAYMENT, referral_new_chat_id))
                            await db.commit()

                            logging.info(f"Бонус за оплату начислен пользователю {referral_old_chat_id}.")

                            # Уведомляем реферера
                            try:
                                message = (
                                    f"💰 Ваш реферал (ID: {referral_new_chat_id}) оплатил подписку!\n"
                                    f"🎁 Вам начислено 10 бонусных дней! Спасибо за приглашение новых пользователей! 😊"
                                )
                                await bot.send_message(referral_old_chat_id, message)
                                await send_admin_log(bot,f"🎁🎁 Пользователю {referral_old_chat_id} начислено 10 дней после оплаты !")
                            except Exception as e:
                                logging.error(f"Ошибка при отправке уведомления рефереру {referral_old_chat_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка при начислении бонуса за оплату: {e}")

    @classmethod
    async def _add_days_to_inviter(cls, inviter_chat_id: int, days: int):
        """
        Добавляет указанное количество дней к сроку подписки пригласившего пользователя.
        """
        query_get_key = "SELECT value_key FROM users_key WHERE chat_id = ?"
        query_update_key = "UPDATE users_key SET value_key = ? WHERE chat_id = ?"

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query_get_key, (inviter_chat_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        logging.warning(f"❌ Пользователь {inviter_chat_id} не найден.")
                        return

                    # Загружаем JSON
                    user_keys = json.loads(row[0])

                    for key in user_keys:
                        if "date_key_off" in key:
                            # Преобразуем дату в нужном формате
                            current_date = datetime.strptime(key["date_key_off"], "%d.%m.%Y %H:%M:%S")
                            new_date = current_date + timedelta(days=days)

                            # Обновляем значение в JSON
                            key["date_key_off"] = new_date.strftime("%d.%m.%Y %H:%M:%S")

                            # Сохраняем обновленный JSON
                            updated_json = json.dumps(user_keys)

                            await db.execute(query_update_key, (updated_json, inviter_chat_id))
                            await db.commit()
                            logging.info(f"✅ {days} бонусных дней добавлено пользователю {inviter_chat_id}.")
                            return

                    logging.warning(f"⚠️ У пользователя {inviter_chat_id} нет активных ключей.")

        except Exception as e:
            logging.error(f"❌ Ошибка при добавлении бонусных дней: {e}")

    #
    # async def check_activation(self) -> bool:
    #     """
    #     Проверяет, активирован ли реферал (если приглашенный пользователь добавил сервер).
    #     """
    #     if self.bonus_status == "bonus_2_days_added":
    #         logging.info(f"Бонус за активацию уже начислен для {self.referral_new_chat_id}.")
    #         return False
    #
    #     from models.UserCl import UserCl
    #     user = await UserCl.load_user(self.referral_new_chat_id)
    #     if not user or not user.servers:
    #         return False
    #
    #     self.referral_status = "active"
    #     await self.update_referral_status()
    #     await self.add_bonus_days(bonus_days=2, bonus_type="bonus_2_days_added")
    #     return True
    #
    # async def check_payment(self) -> bool:
    #     """
    #     Проверяет, оплатил ли приглашенный пользователь подписку.
    #     """
    #     if self.bonus_status == "bonus_14_days_added":
    #         logging.info(f"Бонус за оплату уже начислен для реферала {self.referral_new_chat_id}.")
    #         return False
    #
    #     from models.UserCl import UserCl
    #     user = await UserCl.load_user(self.referral_new_chat_id)
    #     if not user or not user.servers:
    #         return False
    #
    #     for server in user.servers:
    #         has_paid_key = await server.has_paid_key.get()
    #         if has_paid_key > 0:  # Если пользователь оплатил хотя бы один ключ
    #             self.referral_status = "paid"
    #             await self.update_referral_status()
    #             await self.add_bonus_days(bonus_days=14, bonus_type="bonus_14_days_added")
    #             return True
    #
    #     return False
    #
    # async def add_bonus_days(self, bonus_days: int, bonus_type: str):
    #     """
    #     Добавляет бонусные дни пользователю, пригласившему реферала.
    #     """
    #     from models.UserCl import UserCl
    #     inviter = await UserCl.load_user(self.referral_old_chat_id)
    #     if not inviter or not inviter.servers:
    #         return
    #
    #     for server in inviter.servers:
    #         current_date_key_off = await server.date_key_off.get()
    #         current_date_key_off = datetime.strptime(current_date_key_off, "%d.%m.%Y %H:%M:%S")
    #         new_date_key_off = current_date_key_off + timedelta(days=bonus_days)
    #         await server.date_key_off.set(new_date_key_off.strftime("%d.%m.%Y %H:%M:%S"))
    #
    #     self.bonus_status = bonus_type
    #     self.date_bonus_awarded = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     await self.update_referral_status()
    #
    # async def update_referral_status(self):
    #     """
    #     Обновляет статус реферала в базе данных.
    #     """
    #     query = "UPDATE referrals SET referral_status = ?, bonus_status = ? WHERE referral_old_chat_id = ? AND referral_new_chat_id = ?"
    #     try:
    #         async with aiosqlite.connect(os.getenv('database_path_local')) as db:
    #             await db.execute(query, (
    #                 self.referral_status, self.bonus_status,
    #                 self.referral_old_chat_id, self.referral_new_chat_id
    #             ))
    #             await db.commit()
    #     except Exception as e:
    #         logging.error(f"Ошибка при обновлении статуса реферала: {e}")
    #         raise
    #
    #
    #
    # async def to_dict(self) -> Dict:
    #     """
    #     Преобразует объект реферала в словарь.
    #     """
    #     return {
    #         "referral_old_chat_id": self.referral_old_chat_id,
    #         "referral_new_chat_id": self.referral_new_chat_id,
    #         "date_referred": self.date_referred,
    #         "referral_status": self.referral_status,
    #         "bonus_status": self.bonus_status,
    #         "date_bonus_awarded": self.date_bonus_awarded,
    #     }
