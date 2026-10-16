from pyrogram import Client

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

        self._user: FearUser
        self._bot: FearBot

    @property
    def clients(self) -> list[Client]:
        return [self._user, self._bot]

    def __create_user(self) -> None:
        self._user = FearUser(
            self.name,
            self,
            self.api_id,
            self.api_hash,
            self.phone_number,
            self.password,
            **get_settings("src/client/core/plugins/user"),
        )

    def __create_bot(self) -> None:
        self._bot = FearBot(
            f"{self.name}_bot",
            self.bot_token,
            self._user.me.id if self._user.me else 0,
            self,
            self.api_id,
            self.api_hash,
            **get_settings("src/client/core/plugins/bot"),
        )

    async def setup(self) -> None:
        self.__create_user()
        async with self._user:
            self.bot_token = await self._user.get_bot_token()
            self.__create_bot()

            async with self._bot:
                await self._user.setup_bot_settings(self._bot)
