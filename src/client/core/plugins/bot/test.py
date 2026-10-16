from typing import cast

from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.client.core.types import FearBot

kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton("Тест", callback_data="test")]]
)


@Client.on_business_message(filters.command("testb", "."))
async def test_on_business(client: Client, message: types.Message):
    await message.answer("Бизнес сообщение", reply_markup=kb)


@Client.on_callback_query(filters.regex("test"))
async def test_callback_query(client: Client, callback: types.CallbackQuery):
    client = cast(FearBot, client)
    await callback.answer(f"{callback.from_user.id} нажал!")

    if callback.chat and callback.chat.id:
        await client.client._user.send_message(callback.chat.id, "Ты нажал.")
