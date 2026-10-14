import logging

from pyrogram import Client

log = logging.getLogger(__name__)


@Client.on_start()
async def on_start(client: Client):
    log.info("Bot started!")

    await client.send_message("me", "Client started!")


@Client.on_stop()
async def on_stop(client: Client):
    log.info("Bot stopped!")
