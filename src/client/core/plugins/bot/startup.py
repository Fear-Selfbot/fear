from typing import cast

from pyrogram import Client

from src.client.core.types import FearBot


@Client.on_start()
async def on_start(client: Client):
    client = cast(FearBot, client)

    if client.owner_id:
        await client.send_message(client.owner_id, "FearBot started!")
