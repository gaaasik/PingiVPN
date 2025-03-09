import logging

from .base_processor import BaseResultProcessor
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ResultChangeEnable(BaseResultProcessor):
    async def process(self, task_data: dict):
        chat_id = task_data.get('chat_id')
        enable_status = task_data.get('enable')
        status_task = task_data.get('status')
        protocol = task_data.get('protocol')
        us = await UserCl.load_user(chat_id)
        uuid_id = None
        user_ip = None
        if protocol == "vless":
            uuid_id = task_data.get('uuid_value')
        elif protocol == "wireguard":
            user_ip = task_data.get('user_ip')

        if not us:
            logging.error(f"Ошибка у enable в result_change_enable. От chat_id = {chat_id}")
            await send_admin_log(bot,
                                 f"😈❌ Пользователь {chat_id} НЕ изменил состояние status={status_task}")
            return

        identifier = None
        if protocol == "vless":
            identifier = task_data.get('uuid_value')
        elif protocol == "wireguard":
            identifier = task_data.get('user_ip')

        if identifier:
            await self.update_enable_status(us, identifier, enable_status, protocol)

        logging.info(f"Получена и обработана задача result_change_enable. От chat_id = {chat_id}")
        await send_admin_log(bot,
                             f"😈 Пользователь {chat_id} изменил состояние на {enable_status} (в db:{await us.active_server.enable.get()}), status={status_task}")

    async def update_enable_status(self, us: UserCl, identifier: str, enable_status: bool, protocol: str):
        """
        Универсальная функция обновления enable_status для VLESS и WireGuard.
        """

        current_identifier = await us.active_server.uuid_id.get() if protocol == "vless" else await us.active_server.user_ip.get()

        if current_identifier == identifier:
            await us.active_server.enable.set_enable_admin(enable_status)
            logging.info(f"Успешно обновлен enable для активного ключа {identifier}")
        else:
            # Проверяем history_key_list
            for key in us.history_key_list:
                key_identifier = await key.uuid_id.get() if protocol == "vless" else await key.user_ip.get()
                if key_identifier == identifier:
                    await key.enable.set_enable_admin(enable_status)
                    logging.info(f"✅ Обновлен ключ в history_key_list: {identifier}, enable={enable_status}")
                    return

            logging.error(f"⚠️ Ошибка: идентификатор {identifier} не найден ни в active_server, ни в history_key_list")
            await send_admin_log(f"⚠️😈 Ошибка: идентификатор {identifier} не найден ни в active_server, ни в history_key_list chat_id={us.chat_id}")


        # if us:
        #     if await us.active_server.name_protocol.get() == "vless":
        #         now_uuid_id = await us.active_server.uuid_id.get()
        #         if now_uuid_id == uuid_id:
        #             await us.active_server.enable.set_enable_admin(enable_status)
        #         else:
        #             logging.error(
        #                 f"обработка result_change_enable: пришел ответ с uuid_value = {uuid_id}, а у пользователя с chat_id = {chat_id} сейчас uuid_id = {now_uuid_id}")
        #             return
        #     elif await us.active_server.name_protocol.get() == "wireguard":
        #         now_user_ip = await us.active_server.user_ip.get()
        #         if now_user_ip == user_ip:
        #             await us.active_server.enable.set_enable_admin(enable_status)
        #         else:
        #             logging.error(
        #                 f"обработка result_change_enable: пришел ответ с user_ip = {user_ip}, а у пользователя с chat_id = {chat_id} сейчас user_ip = {now_user_ip}")
        #             return
        #
        #     logging.info(f"Получена и обработана задача result_change_enable. От chat_id = {chat_id}")
        #     await send_admin_log(bot,
        #                          f"😈Пользователь {chat_id} изменил состояние на {enable_status} (в db:{await us.active_server.enable.get()}), status={status_task}")
        #
        # else:
        #     logging.error(f"Ошибка у enable в result_change_enable. От chat_id = {chat_id}")
        #     await send_admin_log(bot,
        #                          f"😈❌Пользователь {chat_id} НЕ изменил состояние, сейчас {await us.active_server.enable.get()}, а пришло enable=NONE status={status_task}")
        #




        # if us and enable_status is not None:    result_change_enable_user
        #     await us.active_server.enable.set_enable_admin(enable_status)
        #     logging.info(f"Получена и обработана задача result_change_enable. От chat_id = {chat_id}")
        #     await send_admin_log(bot, f"😈Пользователь {chat_id} изменил состояние на {enable_status} (в db:{await us.active_server.enable.get()}), status={status_task}")
        #
        # else:
        #     logging.error(f"Ошибка у enable в result_change_enable. От chat_id = {chat_id}")
        #     await send_admin_log(bot,
        #                          f"😈❌Пользователь {chat_id} НЕ изменил состояние, сейчас {await us.active_server.enable.get()}, а пришло enable=NONE status={status_task}")
        #
        #

