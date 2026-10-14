from typing import cast as TypeCast

from pyrogram import Client

from .main import FearBot, FearClient

__all__ = ["FearBot", "FearClient"]


def cast(client: Client) -> FearClient:
    return TypeCast(FearClient, client)
