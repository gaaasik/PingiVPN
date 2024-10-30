from aiogram import Router
from aiogram.types import CallbackQuery







router = Router()


@router.callback_query(lambda c: c.data == "about_vpn")
async def handle_about_vpn(callback_query: CallbackQuery):
    await callback_query.answer("Всё о PingiVPN: функционал пока не реализован.")