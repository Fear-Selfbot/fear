from dispyro import Dispatcher
from pyrogram import Client
from pyrogram.enums import ClientPlatform

from config import config

from .handlers import get_routers


def get_sessions() -> list[str]:
    return [f.stem for f in config.SESSIONS_DIR.glob("*.session")]


class FearCore:
    def __init__(self):
        pass

    async def start(self) -> None:
        await self.__load_sessions()

    async def __create_first_session(self) -> str:
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

        await app.start()
        await app.stop()

        return config.NAME

    async def __create_clients(self, names: list[str]) -> list[Client]:

        clients: list[Client] = []

        for name in names:
            plugins = dict(root="src/client/handlers/plugins")  # noqa: C408
            client = Client(
                name=name,
                proxy=config.proxy.http if config.proxy.HOST != "localhost" else None,
                client_platform=ClientPlatform.DESKTOP,
                device_model="Desktop",
                system_version="Windows 11 x64",
                app_version="7.2.9 x64",
                workdir=str(config.SESSIONS_DIR),
                plugins=plugins,
            )

            clients.append(client)

        return clients

    async def __load_sessions(self) -> None:

        files = get_sessions()

        if not files:
            files.append(await self.__create_first_session())

        clients = await self.__create_clients(files)
        dp = Dispatcher(*clients, numbers=[1, 2, 3])

        dp.add_routers(*get_routers())

        await dp.start()
