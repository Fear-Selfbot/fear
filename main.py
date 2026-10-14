import asyncio
import logging

from kurigram_utils import install_event_loop

from src.client.main import FearCore

# Install custom asyncio event loop
install_event_loop()

log = logging.getLogger(__name__)


async def main():
    fearCore = FearCore()
    await fearCore.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(main())
