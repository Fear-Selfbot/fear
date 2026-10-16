from typing import cast

from pyrogram import Client, types

from src.client.core.mixins.user import WaitMessage
from src.client.core.types import FearUser


def isFromChat(wait: WaitMessage, message: types.Message) -> bool:
    chat, user = message.chat, message.from_user
    fromChat = bool(chat and chat.id == wait.from_chat)
    fromUser = bool(user and user.username == wait.from_chat)
    return fromChat or fromUser


def isFromUser(wait: WaitMessage, message: types.Message) -> bool:
    user = message.from_user
    if not wait.wait_from:
        return True
    return bool(user and user.username == wait.wait_from) or bool(
        user and user.id == wait.wait_from
    )


@Client.on_message()
async def waiter(client: Client, message: types.Message):
    client = cast(FearUser, client)
    chat_id = message.chat.id if message.chat else 0
    username = message.from_user.username if message.from_user else ""
    wait_message = client.message_pool.get(chat_id) or client.message_pool.get(username)

    if (
        wait_message is not None
        and wait_message.is_waiting
        and isFromChat(wait_message, message)
        and isFromUser(wait_message, message)
    ):
        wait_message.message = message
        wait_message.event.set()
        message.stop_propagation()
