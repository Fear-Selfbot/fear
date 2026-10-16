import asyncio
import logging

from kurigram_utils import install_event_loop

from config import config

# from src.client.main import FearCore

# Install custom asyncio event loop
install_event_loop()

from src.client.core.client import FearClient

log = logging.getLogger(__name__)


async def main():
    client = FearClient(
        name=config.NAME,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        phone_number=config.PHONE,
        password=config.PASSWORD,
    )

    await client.setup()

    # await compose(client.clients)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
