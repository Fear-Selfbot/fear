import asyncio
from dataclasses import dataclass

from pyrogram import Client as PyroClient
from pyrogram.types import Message


@dataclass
class WaitMessage:
    event: asyncio.Event
    message: Message | None = None
    is_waiting: bool = False
    fromChat: str | int | None = None
    waitFrom: str | int | None = None


class FearUser(PyroClient):
    """Userbot instance of fear client"""

    def __init__(
        self,
        name: str,
        api_id: int | None = None,
        api_hash: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
        **kwargs,
    ):
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
        api_id: int | None = None,
        api_hash: str | None = None,
        **kwargs,
    ):
        super().__init__(
            name,
            api_id,
            api_hash,
            **kwargs,
        )
