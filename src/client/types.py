import asyncio
from dataclasses import dataclass

from pyrogram.types import Message


@dataclass
class WaitMessage:
    event: asyncio.Event
    message: Message | None = None
    is_waiting: bool = False
    fromChat: str | int | None = None
    waitFrom: str | int | None = None
