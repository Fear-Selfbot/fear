import asyncio
import logging

from kurigram_utils import install_event_loop
from pyrogram import compose

from config import config

# from src.client.main import FearCore

# Install custom asyncio event loop
install_event_loop()


from src.core.client import FearClient

log = logging.getLogger(__name__)


async def main():
    log.info("Preparing Fear clients")
    client = FearClient(
        name=config.NAME,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        phone_number=config.PHONE,
        password=config.PASSWORD,
    )

    try:
        await client.setup()
    except Exception:
        log.exception("Fear client setup failed")
        raise

    log.info("Starting Telegram clients")
    try:
        await compose(client.clients)
    except Exception:
        log.exception("Telegram clients stopped with an error")
        raise
    finally:
        log.info("Fear has stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
