from datetime import datetime, timedelta

async def is_trial_ending_soon(date_key_off: str, days_until_end: int = 2) -> bool:
    """
    Проверяет, заканчивается ли пробный период через заданное количество дней.
    """
    trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
    return (trial_end_date - timedelta(days=days_until_end)).date() <= datetime.now().date()


async def is_trial_ended(date_key_off: str) -> bool:
    """
    Проверяет, завершился ли пробный период.
    """
    trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
    return trial_end_date.date() < datetime.now().date()
