from .types import FearBot, FearUser
from .utils.settings import get_settings


class FearClient:
    def __init__(
        self,
        name: str,
        bot_token: str,
        api_id: int | None = None,
        api_hash: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
    ):
        self.name = name
        self.bot_token = bot_token
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.password = password

        self._user: FearUser
        self._bot: FearBot

    def __create_user(self) -> None:
        self._user = FearUser(
            self.name,
            self.api_id,
            self.api_hash,
            self.phone_number,
            self.password,
            **get_settings(),
        )

    async def setup(self) -> None:
        self.__create_user()
