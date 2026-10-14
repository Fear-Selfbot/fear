from dispyro import Router
from pyrogram import Client, filters, types

router = Router()


@router.message(filters.command("test", prefixes="."))
async def handler(_: Client, message: types.Message, numbers: list[int]):
    formatted_numbers = ", ".join(map(str, numbers))
    text = f"Entered numbers: {formatted_numbers}"
    await message.edit_text(text=text)
