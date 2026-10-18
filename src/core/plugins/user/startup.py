from typing import cast

from pyrogram import Client

from src.core.types import FearUser


@Client.on_start()
async def on_start(client: Client):
    client = cast(FearUser, client)

    if client.client.is_setup:
        return

    if client.client.restart_message:
        await client.client.restart_message.edit("Перезагружен.")
        client.client.restart_message = None
    else:
        await client.send_message("me", "FearUser started!")
