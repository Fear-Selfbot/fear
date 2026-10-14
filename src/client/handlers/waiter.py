from dispyro import Router
from pyrogram import Client, types

from src.client.filters import clientBot
from src.client.types import WaitMessage

router = Router("waiter")
router.message.filter(~clientBot)


def isFromChat(wait: WaitMessage, message: types.Message) -> bool:
    chat, user = message.chat, message.from_user
    fromChat = bool(chat and chat.id == wait.fromChat)
    fromUser = bool(user and user.username == wait.fromChat)
    return fromChat or fromUser


def isFromUser(wait: WaitMessage, message: types.Message) -> bool:
    user = message.from_user
    if not wait.waitFrom:
        return True
    return bool(user and user.username == wait.waitFrom) or bool(
        user and user.id == wait.waitFrom
    )


@router.message()
async def waitHandler(client: Client, message: types.Message):
    waiting_message: WaitMessage | None = getattr(client, "waitingMessage", None)
    if not waiting_message:
        return

    if (
        waiting_message.is_waiting
        and isFromChat(waiting_message, message)
        and isFromUser(waiting_message, message)
    ):
        waiting_message.message = message
        waiting_message.event.set()
        message.stop_propagation()
