from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()


@router.message(lambda message: message.text == "Проверить скорость")
async def handle_speed_test(message: types.Message):
    # Создаем инлайн-кнопку с ссылкой на Speedtest
    speedtest_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть Speedtest", url="https://www.speedtest.net/ru#")]
        ]
    )

    # Отправляем сообщение с кнопкой для проверки скорости
    await message.answer(
        "Нажмите на кнопку ниже, чтобы перейти на сайт Speedtest и проверить скорость вашего интернет-соединения:",
        reply_markup=speedtest_button)