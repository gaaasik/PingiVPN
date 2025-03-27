from aiogram.fsm.state import StatesGroup, State

class GeneralStates(StatesGroup):
    main_menu = State()

class FeedbackStates(StatesGroup):
    choosing_feedback_type = State()

class NotificationStates(StatesGroup):
    viewing_notification = State()
    interacting_with_notification = State()
