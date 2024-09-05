# bot/middlewares/throttling.py
from aiogram import BaseMiddleware
from aiogram.types import Message
#from aiogram.utils.exceptions import Throttled
import asyncio
from typing import Dict

from bot.handlers.cleanup import store_message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 1):
        self.rate_limit = rate_limit
        self._user_last_message: Dict[int, float] = {}
        super().__init__()

    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        current_time = asyncio.get_event_loop().time()

        if user_id in self._user_last_message:
            elapsed_time = current_time - self._user_last_message[user_id]
            if elapsed_time < self.rate_limit:
                # Сообщение было отправлено слишком быстро, пропускаем обработчик
                response = await event.answer("Вы отправляете сообщения слишком быстро! Пожалуйста, подождите немного.")
                # Сохраняем сообщение в базе данных
                await store_message(response.chat.id, response.message_id, response.text, 'user')

                return

        # Обновляем время последнего сообщения пользователя
        self._user_last_message[user_id] = current_time

        # Вызываем обработчик
        return await handler(event, data)
