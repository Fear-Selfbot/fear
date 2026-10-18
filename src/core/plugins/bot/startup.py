from typing import cast

from pyrogram import Client

from src.core.types import FearBot


@Client.on_start()
async def on_start(client: Client):
    client = cast(FearBot, client)

    if client.client.restart_message:
        return

    if client.client.is_setup:
        return

    if client.owner_id:
        await client.send_message(client.owner_id, "FearBot started!")
