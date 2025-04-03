from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_search_method = State()
    waiting_for_chat_id = State()
    waiting_for_action = State()
    waiting_for_bonus_days = State()
    waiting_for_nickname = State()
    waiting_for_vless_key = State()
    waiting_for_wireguard_file = State()
    waiting_for_friend_confirmation = State()
    main_menu_user = State()
