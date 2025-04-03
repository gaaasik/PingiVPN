from aiogram.fsm.state import StatesGroup, State

class GeneralStates(StatesGroup):
    main_menu = State()

class FeedbackStates(StatesGroup):
    choosing_feedback_type = State()

    rating_speed = State()
    rating_difficulty = State()
    rating_comment = State()

    # Могут быть добавлены позже
    submitting_suggestion = State()
    submitting_issue = State()

class NotificationStates(StatesGroup):
    viewing_notification = State()
    interacting_with_notification = State()
