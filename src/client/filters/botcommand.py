from pyrogram import Client, filters


async def _clientBot(_, client: Client, query):
    if client.me:
        return client.me.is_bot
    return False


clientBot = filters.create(_clientBot)
