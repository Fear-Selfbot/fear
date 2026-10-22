from typing import Protocol, cast

from fear_module import (
    ClientType,
    Command,
    FearBot,
    FearModule,
    FearUser,
)
from fear_module.protocols import FearClientProtocol, FearUserProtocol
from pyrogram import Client, filters, types
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, User

helpUserCommand = Command("help", ".", "Returns all commands", ClientType.USER)
helpBotCommand = Command("help", "/", "Returns all commands", ClientType.BOT)
reloadCommand = Command("reload", ".", "Reload all modules", ClientType.USER)


class FearUserExtended(FearUserProtocol, Protocol):
    @property
    def me(self) -> User | None: ...


class FearClientExtended(FearClientProtocol, Protocol):
    @property
    def user(self) -> FearUserExtended: ...

    restart_message: Message | None


class SystemModule(FearModule):
    name: str = "System"
    version: str = "1.0.0"
    author: str = "Keva1z"

    def __init__(self, client: FearClientExtended):
        super().__init__(client)
        self.client: FearClientExtended = client
        self.add_commands([helpUserCommand, helpBotCommand, reloadCommand])

    def register(self):
        reloadCommand.add_handler(
            MessageHandler(reload_handler, reloadCommand.filter & filters.me)
        )
        helpUserCommand.add_handler(
            MessageHandler(help_handler, helpUserCommand.filter & filters.me)
        )
        user = self.client.user.me
        if user:
            helpBotCommand.add_handler(
                MessageHandler(
                    help_handler_bot,
                    helpBotCommand.filter & filters.chat(user.id),
                )
            )


async def help_handler(client: Client, message: types.Message):
    client = cast(FearUser, client)

    commands = ""

    for module in client.client.modules:
        commands += module.get_commands(ClientType.USER) + "\n"
        if (
            message.chat and message.chat.type and message.chat.type.name == "PRIVATE"
        ) and (message.from_user and message.from_user.id != message.chat.id):
            commands += module.get_commands(ClientType.SECRETARY).replace(
                f"{module.header}\n", ""
            )
        commands += "\n"

    await message.edit(commands)


async def help_handler_bot(client: Client, message: types.Message):
    client = cast(FearBot, client)

    commands = ""

    for module in client.client.modules:
        commands += module.get_commands(ClientType.BOT) + "\n\n"

    await message.answer(commands)


async def reload_handler(client: Client, message: types.Message):
    client = cast(FearUser, client)
    fear_client = cast(FearClientExtended, client.client)
    msg = await message.edit("Модули перезагружаются")
    if msg:
        fear_client.restart_message = msg
    client.client.schedule_restart()
