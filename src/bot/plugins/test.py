import logging

from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger(__name__)


@Client.on_business_connection()
async def on_business_connection(client: Client, bc: types.BusinessConnection):
    print(f"Connection {bc.id} active: {bc.is_enabled} for user {bc.user.id}")


kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton("Тест", callback_data="testdata")]]
)


@Client.on_business_message(filters.command("testb", "."))
async def testMessage(client: Client, message: types.Message):
    biz_conn_id = message.business_connection_id

    if biz_conn_id and message.text:
        # Reply on behalf of the user/business account
        await message.delete()
        await message.answer("test", reply_markup=kb)


@Client.on_callback_query()
async def testData(client: Client, callback: types.CallbackQuery):
    await callback.answer()

    if callback.message:
        await callback.message.edit("Нажал...")
