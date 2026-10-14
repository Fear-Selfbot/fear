from dispyro import Router
from pyrogram import Client, filters, types

from src.client import cast
from src.client.filters import clientBot

router = Router("tests")


@router.message(filters.command("test", prefixes=".") & ~clientBot)
async def handler(client: Client, message: types.Message):
    client = cast(client)

    await message.edit("тест")
    if message.chat and message.chat.id:
        msg = await client.send_and_wait_message(
            message.chat.id, "скажи чет", message.chat.id
        )
        if not msg:
            return
        await msg.answer("Это автоответ")
        msg = await client.send_and_wait_message(
            message.chat.id, "еще чето скажи", message.chat.id
        )
        if not msg:
            return
        await msg.answer("Автоответ 2")


@router.message(filters.command("test", prefixes="/") & clientBot)
async def handler2(client: Client, message: types.Message):
    await message.answer("Im a bot")
