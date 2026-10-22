from typing import Generator
import asyncio
import logging

from fear_module import ClientType, FearModule
from pyrogram import Client
from pyrogram.handlers import Handler
from pyrogram.types import Message

from config import config
from src.core.module.loader import ModuleLoader

from .types import FearBot, FearUser
from .utils.settings import get_settings

log = logging.getLogger(__name__)


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
        self._remove_module_handlers(self._loaded_modules)
        log.info("Unloaded %d modules", len(self._loaded_modules))
        self._loaded_modules.clear()

    def _handlers_for(self, modules: list[FearModule]):
        for module in modules:
            yield self._user, module.user_handlers
            yield self._bot, module.bot_handlers
            yield self._bot, module.get_handlers(ClientType.SECRETARY)

    def _add_module_handlers(self, modules: list[FearModule]) -> None:
        added: list[tuple[Client, Handler]] = []
        try:
            for client, handlers in self._handlers_for(modules):
                for handler in handlers:
                    client.add_handler(handler)
                    added.append((client, handler))
        except Exception:
            for client, handler in reversed(added):
                try:
                    client.remove_handler(handler)
                except Exception:
                    log.exception(
                        "Could not roll back a partially added module handler"
                    )
            raise

    def _remove_module_handlers(self, modules: list[FearModule]) -> None:
        for client, handlers in self._handlers_for(modules):
            for handler in handlers:
                client.remove_handler(handler)

    def load_modules(self):
        previous = self._loaded_modules
        clients_connected = any(client.is_connected for client in self.clients)
        try:
            loaded = ModuleLoader(config.MODULES_DIR).load(self)
        except Exception:
            # stop(clear_handlers=True) removes handlers before a restart reload.
            if previous and not clients_connected:
                self._add_module_handlers(previous)
            raise

        if clients_connected:
            self._remove_module_handlers(previous)
        try:
            self._add_module_handlers(loaded)
        except Exception:
            if previous:
                self._add_module_handlers(previous)
            raise

        self._loaded_modules = loaded
        log.info("Loaded %d modules", len(loaded))

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
        log.info("Setting up the user Telegram client")
        self.__create_user()
        async with self._user:
            log.info("Requesting the linked bot token from BotFather")
            self.bot_token = await self._user.get_bot_token()
            self.__create_bot()

            log.info("Setting up the linked bot client")
            async with self._bot:
                await self._user.setup_bot_settings(self._bot)
        self.is_setup = False
        log.info("Loading Fear modules")
        self.load_modules()

    async def restart_clients(self):
        await asyncio.gather(
            *(client.stop(block=True, clear_handlers=True) for client in self.clients)
        )

        try:
            self.load_modules()
        except Exception:
            log.exception("Module reload failed; restarting with the previous modules")
            await asyncio.gather(*(client.start() for client in self.clients))
            if self.restart_message:
                await self.restart_message.edit(
                    "Не удалось перезагрузить модули; восстановлен предыдущий набор."
                )
                self.restart_message = None
            return

        await asyncio.gather(*(client.start() for client in self.clients))

    def schedule_restart(self):
        asyncio.get_running_loop().call_soon(
            lambda: asyncio.create_task(self.restart_clients())
        )
