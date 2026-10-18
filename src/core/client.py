import asyncio

from fear_module import ClientType, FearModule
from pyrogram import Client
from pyrogram.types import Message

from config import config
from src.core.module.loader import ModuleLoader

from .types import FearBot, FearUser
from .utils.settings import get_settings


class FearClient:
    def __init__(
        self,
        name: str,
        api_id: int | None = None,
        api_hash: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
    ):
        self.name = name
        self.bot_token: str
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.password = password

        self.restart_message: Message | None = None
        self.is_setup: bool = True

        self._loaded_modules: list[FearModule] = []
        self._user: FearUser
        self._bot: FearBot

    @property
    def modules(self) -> list[FearModule]:
        return self._loaded_modules

    @property
    def clients(self) -> list[Client]:
        return [self._user, self._bot]

    @property
    def user(self) -> FearUser:
        return self._user

    @property
    def bot(self) -> FearBot:
        return self._bot

    def unload_modules(self):
        for module in self._loaded_modules:
            for handler in module.user_handlers:
                self._user.remove_handler(handler)
            for handler in module.bot_handlers:
                self._bot.remove_handler(handler)
        print(f"Unloaded {len(self._loaded_modules)} modules")
        self._loaded_modules.clear()

    def load_modules(self):
        self.unload_modules()
        self._loaded_modules = ModuleLoader(config.MODULES_DIR).load(self)

        for module in self._loaded_modules:
            for handler in module.user_handlers:
                self._user.add_handler(handler)
            for handler in module.bot_handlers:
                self._bot.add_handler(handler)
            for handler in module.get_handlers(ClientType.SECRETARY):
                self._bot.add_handler(handler)

        print(f"Loaded {len(self._loaded_modules)} modules")

    def __create_user(self) -> None:
        self._user = FearUser(
            self.name,
            self,
            self.api_id,
            self.api_hash,
            self.phone_number,
            self.password,
            **get_settings("src/core/plugins/user"),
        )

    def __create_bot(self) -> None:
        self._bot = FearBot(
            f"{self.name}_bot",
            self.bot_token,
            self._user.me.id if self._user.me else 0,
            self,
            self.api_id,
            self.api_hash,
            **get_settings("src/core/plugins/bot"),
        )

    async def setup(self) -> None:
        self.__create_user()
        async with self._user:
            self.bot_token = await self._user.get_bot_token()
            self.__create_bot()

            async with self._bot:
                await self._user.setup_bot_settings(self._bot)
        self.is_setup = False
        self.load_modules()

    async def restart_clients(self):
        await asyncio.gather(
            *(client.stop(block=True, clear_handlers=True) for client in self.clients)
        )

        self.load_modules()

        await asyncio.gather(*(client.start() for client in self.clients))

    def schedule_restart(self):
        asyncio.get_running_loop().call_soon(
            lambda: asyncio.create_task(self.restart_clients())
        )
