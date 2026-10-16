from pyrogram import Client


@Client.on_start()
async def on_start(client: Client):
    await client.send_message("me", "FearUser started!")
