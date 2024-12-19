import logging
from datetime import datetime, timedelta

# async def is_trial_ending_soon(date_key_off: str, days_until_end: int = 2) -> bool:
#     """
#     Проверяет, заканчивается ли пробный период через заданное количество дней.
#     """
#     trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
#     return (trial_end_date - timedelta(days=days_until_end)).date() <= datetime.now().date()


async def is_trial_ended(date_key_off: str) -> bool:
    """
    Проверяет, завершился ли пробный период или он истекает сегодня, приводя все даты к формату YYYY-MM-DD.
    """
    try:
        # Преобразование строки в datetime и получение даты в формате YYYY-MM-DD
        trial_end_date = datetime.strptime(date_key_off.strip(), "%d.%m.%Y %H:%M:%S").date()
        current_date = datetime.now().date()

        # Приводим обе даты к строке формата YYYY-MM-DD для единообразного сравнения
        trial_end_date_str = trial_end_date.strftime("%Y-%m-%d")
        current_date_str = current_date.strftime("%Y-%m-%d")

        # Преобразуем строки обратно в datetime.date
        trial_end_date = datetime.strptime(trial_end_date_str, "%Y-%m-%d").date()
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()

        # Сравнение дат
        result = trial_end_date <= current_date
        logging.info(
            f"is_trial_ended: date_key_off={date_key_off}, trial_end_date={trial_end_date}, "
            f"current_date={current_date}, result={result}"
        )
        return result
    except ValueError as ve:
        logging.error(f"Ошибка преобразования даты: {ve}")
        return False
    except Exception as e:
        logging.error(f"Ошибка в is_trial_ended: {e}")
        return False

