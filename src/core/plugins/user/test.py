from pyrogram import Client, filters, types


@Client.on_message(filters.command("test", "."))
async def test_on_message(client: Client, message: types.Message):
    await message.answer("Обычное сообщение")
