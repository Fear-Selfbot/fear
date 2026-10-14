import logging

from kurigram_utils import install_event_loop
from pyrogram import Client
from pyrogram.enums import ClientPlatform

from config import config

# Install custom asyncio event loop
install_event_loop()

log = logging.getLogger(__name__)

# Telegram Client
app = Client(
    name=config.NAME,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    phone_number=config.PHONE,
    password=config.PASSWORD,
    proxy=config.proxy.http if config.proxy.HOST != "localhost" else None,
    client_platform=ClientPlatform.DESKTOP,
    device_model="Desktop",
    system_version="Windows 11 x64",
    app_version="7.2.9 x64",
    workdir=str(config.SESSIONS_DIR),
)


@app.on_start()
async def on_start(client: Client):
    log.info("Bot started!")

    await client.send_message("me", "Client started!")


@app.on_stop()
async def on_stop(client: Client):
    log.info("Bot stopped!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app.run()
