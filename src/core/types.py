from typing import TYPE_CHECKING

from pyrogram import Client as PyroClient

from src.core.mixins.user import UserMethods

if TYPE_CHECKING:
    from .client import FearClient


class FearUser(UserMethods, PyroClient):
    """Userbot instance of fear client"""

    def __init__(
        self,
        name: str,
        client: FearClient,
        api_id: int | None = None,
        api_hash: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
        **kwargs,
    ):
        self.client = client
        super().__init__(
            name,
            api_id,
            api_hash,
            phone_number=phone_number,
            password=password,
            **kwargs,
        )


class FearBot(PyroClient):
    """Bot instance of fear client"""

    def __init__(
        self,
        name: str,
        bot_token: str,
        owner_id: int,
        client: FearClient,
        api_id: int | None = None,
        api_hash: str | None = None,
        **kwargs,
    ):
        self.client = client
        self.owner_id = owner_id
        super().__init__(
            name,
            api_id,
            api_hash,
            bot_token=bot_token,
            **kwargs,
        )
