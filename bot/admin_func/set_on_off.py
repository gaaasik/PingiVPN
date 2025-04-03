
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# Включение пользователя
@router.callback_query(F.data == "enable_user")
async def enable_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик включения пользователя"""
    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    try:
        # Активируем пользователя
        await user.active_server.enable.set(True)

        # Обновляем сообщение с информацией
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Выключить пользователя", callback_data="disable_user")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu_user")]
        ])

        await callback.message.edit_text(
            f"✅ Пользователь {user.chat_id} включён.\n\nВыберите действие:",
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка при включении пользователя {user.chat_id}: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при включении пользователя.")

    await callback.answer()


# Выключение пользователя
@router.callback_query(F.data == "disable_user")
async def disable_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик выключения пользователя"""
    data = await state.get_data()
    user = data.get("current_user")

    if not user:
        await callback.message.edit_text("❌ Ошибка: пользователь не найден.")
        return

    try:
        # Деактивируем пользователя
        await user.active_server.enable.set(False)

        # Уведомляем пользователя о выключении
        try:
            await callback.bot.send_message(user.chat_id, "❌ Ваш аккаунт был отключен администратором.")
        except Exception as e:
            logging.warning(f"Ошибка при уведомлении пользователя {user.chat_id}: {e}")

        # Обновляем сообщение с информацией
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Включить пользователя", callback_data="enable_user")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu_user")]
        ])

        await callback.message.edit_text(
            f"❌ Пользователь {user.chat_id} отключён.\n\nВыберите действие:",
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Ошибка при выключении пользователя {user.chat_id}: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при выключении пользователя.")

    await callback.answer()









# import os


#
# from aiogram import Router, types, F
# from aiogram.fsm.context import FSMContext
# from aiogram.types import CallbackQuery
# import logging
#
# router = Router()
# # Включение пользователя
# @router.callback_query(F.data == "enable_user")
# async def enable_user(callback: CallbackQuery, state: FSMContext):
#     """Обработчик включения пользователя"""
#     data = await state.get_data()
#     user = data.get("current_user")
#     if not user:
#         await callback.message.answer("Ошибка: пользователь не найден.")
#         return
#
#     try:
#         # Активируем пользователя
#
#
#         await user.active_server.enable.set(True)
#
#         # Уведомляем администратора
#         await callback.message.answer(f"✅ Пользователь {user.chat_id} включен.")
#
#
#     except Exception as e:
#         logging.error(f"Ошибка при включении пользователя {user.chat_id}: {e}")
#         await callback.message.answer("❌ Произошла ошибка при включении пользователя.")
#
#     await callback.answer()
#     await state.clear()
#
#
# # Выключение пользователя
# @router.callback_query(F.data == "disable_user")
# async def disable_user(callback: CallbackQuery, state: FSMContext):
#     """Обработчик выключения пользователя"""
#     data = await state.get_data()
#     user = data.get("current_user")
#
#     if not user:
#         await callback.message.answer("Ошибка: пользователь не найден.")
#         return
#
#     try:
#         # Деактивируем пользователя
#         ##########################################
#         #Доделать
#         await user.active_server.enable.set(False)
#
#         # Уведомляем администратора
#         await callback.message.answer(f"❌ Пользователь {user.chat_id} выключен.")
#
#         # Уведомляем пользователя
#         await callback.bot.send_message(user.chat_id, "Ваш аккаунт был выключен администратором.")
#
#     except Exception as e:
#         logging.error(f"Ошибка при выключении пользователя {user.chat_id}: {e}")
#         await callback.message.answer("❌ Произошла ошибка при выключении пользователя.")
#
#     await callback.answer()
#     await state.clear()