import os

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
import logging

router = Router()
# Включение пользователя
@router.callback_query(F.data == "enable_user")
async def enable_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик включения пользователя"""
    data = await state.get_data()
    user = data.get("current_user")
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден.")
        return

    try:
        # Активируем пользователя


        await user.active_server.enable.set(True)

        # Уведомляем администратора
        await callback.message.answer(f"✅ Пользователь {user.chat_id} включен.")


    except Exception as e:
        logging.error(f"Ошибка при включении пользователя {user.chat_id}: {e}")
        await callback.message.answer("❌ Произошла ошибка при включении пользователя.")

    await callback.answer()
    await state.clear()


# Выключение пользователя
@router.callback_query(F.data == "disable_user")
async def disable_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик выключения пользователя"""
    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        await callback.message.answer("Ошибка: пользователь не найден.")
        return

    try:
        # Деактивируем пользователя
        ##########################################
        #Доделать
        await user.active_server.enable.set(False)

        # Уведомляем администратора
        await callback.message.answer(f"❌ Пользователь {user.chat_id} выключен.")

        # Уведомляем пользователя
        await callback.bot.send_message(user.chat_id, "Ваш аккаунт был выключен администратором.")

    except Exception as e:
        logging.error(f"Ошибка при выключении пользователя {user.chat_id}: {e}")
        await callback.message.answer("❌ Произошла ошибка при выключении пользователя.")

    await callback.answer()
    await state.clear()