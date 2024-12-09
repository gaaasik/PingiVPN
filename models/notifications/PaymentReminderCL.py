class PaymentReminder(NotificationBase):
    async def filter_users_with_unpaid_access(self, batch: List[int]) -> List[int]:
        blocked_users = []

        async def check_user(chat_id: int):
            try:
                user = await UserCl.load_user(chat_id)
                if not user or not user.servers:
                    return None

                for server in user.servers:
                    date_key_off = await server.date_key_off.get()
                    has_paid_key = await server.has_paid_key.get()

                    if await is_trial_ended(date_key_off) and has_paid_key == 0:
                        return chat_id
            except Exception as e:
                print(f"Ошибка при обработке пользователя {chat_id}: {e}")
                return None

        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
        blocked_users = [chat_id for chat_id in results if chat_id is not None]
        return blocked_users

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых завершён пробный период и требуется оплата.
        """
        all_users = await UserCl.get_all_users()
        blocked_users = []
        for batch in self.split_into_batches(all_users):
            blocked_users.extend(await self.filter_users_with_unpaid_access(batch))
        return blocked_users

    def get_message_template(self) -> str:
        return (
            "❌ <b>Ваш доступ заблокирован</b>.\n\n"
            "Пробный период завершён. Для продолжения использования VPN, пожалуйста, оформите подписку:\n\n"
            "💳 <b>Оплатите доступ</b> и наслаждайтесь безопасным соединением без ограничений."
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="buy_vpn")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
        return keyboard
