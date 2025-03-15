import logging

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.admin_func.class_friends.FriendsCL import FriendsManager
from bot.admin_func.keyboards import get_user_service_keyboard
from bot.admin_func.states import AdminStates

router = Router()

# 🔥 Запрос на добавление в список друзей
@router.callback_query(lambda c: c.data == "add_to_friends")
async def add_friend_request(callback_query: CallbackQuery, state: FSMContext):
    """
    Запрашивает подтверждение перед добавлением пользователя в список друзей.
    """
    friend_chat_id = callback_query.message.chat.id  # Чат ID пользователя, которого добавляют

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, дать доступ на год", callback_data=f"confirm_add_friend:{friend_chat_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_friend")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_service")]
    ])

    await callback_query.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите дать этому пользователю доступ на год?</b>",
        parse_mode="HTML",
        reply_markup=confirm_keyboard
    )
    await state.set_state(AdminStates.waiting_for_friend_confirmation)
    await callback_query.answer()

    @router.callback_query(lambda c: c.data.startswith("confirm_add_friend"))
    async def confirm_add_friend(callback_query: CallbackQuery, state: FSMContext):
        """
        Добавляет пользователя в список друзей и продлевает подписку.
        """
        try:
            admin_chat_id = callback_query.from_user.id  # Чат ID админа, который добавляет

            # Получаем данные из состояния
            data = await state.get_data()
            current_user = data.get("current_user")

            if not current_user:
                await callback_query.message.edit_text("❌ Ошибка: не найден пользователь для добавления в друзья.")
                await state.clear()
                return

            friend_chat_id = current_user.chat_id  # Теперь мы берем правильный chat_id

            # Получаем username или имя + фамилию
            friend_username = current_user.user_login.value if current_user.user_login.value else current_user.user_name_full.value

            # Добавляем друга в список
            success = await FriendsManager.add_friend(admin_chat_id, friend_chat_id, friend_username)

            if success:
                text = f"✅ <b>Пользователь {friend_username} успешно добавлен в список друзей и получил 365 дней доступа!</b>"
                logging.info(f"✅ Админ {admin_chat_id} добавил друга: {friend_chat_id} ({friend_username})")
            else:
                text = f"⚠️ <b>{friend_username} уже есть в списке друзей.</b>"
                logging.warning(
                    f"⚠️ Попытка повторного добавления {friend_chat_id} ({friend_username}) в список друзей.")

            keyboard = await get_user_service_keyboard()

            await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await state.clear()
            await callback_query.answer()

        except Exception as e:
            logging.error(f"⚠ Ошибка при добавлении друга: {e}")
            await callback_query.message.answer("❌ Произошла ошибка. Попробуйте позже.")
            await state.clear()


@router.callback_query(lambda c: c.data == "cancel_add_friend")
async def cancel_add_friend(callback_query: CallbackQuery, state: FSMContext):
    """
    Отмена добавления в список друзей и возврат в режим обслуживания.
    """
    keyboard = await get_user_service_keyboard()

    await callback_query.message.edit_text(
        "🚫 <b>Добавление в список друзей отменено.</b>\n\n🔧 Вы вернулись в режим обслуживания.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.clear()
    await callback_query.answer()
