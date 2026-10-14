import asyncio
import logging

from kurigram_utils import install_event_loop

# Pyrogram creates its event loop during import, so install the policy first.
install_event_loop()

from dispyro import Dispatcher, Router
from pyrogram import Client, compose, filters, types

from config import config

plugins = dict(root="src/bot/plugins")

client = Client("Keva1z", workdir=str(config.SESSIONS_DIR))
bot = Client("Keva1z_bot", workdir=str(config.SESSIONS_DIR), plugins=plugins)

clientRouter = Router("Client")
botRouter = Router("Bot")


@client.on_message(filters.command("testClient", "."))
async def test_client(client: Client, message: types.Message):
    await message.answer("Тест Клиент")


@bot.on_message(filters.command("testBot", "."))
async def test_bot(client: Client, message: types.Message):
    await message.answer("Тест бот")


@bot.on_business_message(filters.command("testBot", "."))
async def test_bot_business(client: Client, message: types.Message):
    await message.answer("Тест бот биз.")


async def dispatcher():
    # No types.UpdateBotBusinessConnect
    dp = Dispatcher(*[client, bot], disable_fsm=True, clear_on_prepare=False)

    dp.add_routers(*[clientRouter, botRouter])

    await dp.start()


async def composer():
    # Receiving types.UpdateBotBusinessConnect
    await compose([client, bot])


async def main():
    await dispatcher()
    # await composer()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # asyncio.run(main())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
