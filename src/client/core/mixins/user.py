import asyncio
from dataclasses import dataclass

from pyrogram import Client, types
from pyrogram.types import Message

BOTFATHER = "BotFather"


@dataclass
class WaitMessage:
    event: asyncio.Event
    message: Message | None = None
    is_waiting: bool = False
    from_chat: str | int | None = None
    wait_from: str | int | None = None


class UserMethods(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_pool: dict[str | int, WaitMessage] = {}

    @property
    def botname(self) -> str:
        return f"@FearClient{self.name}_bot"

    async def send_message_wait(
        self,
        chat_id: str | int,
        text: str,
        wait_from: str | int | None = None,
        delete: bool = False,
        timeout: int = 30,
    ) -> types.Message | None:
        if chat_id in self.message_pool:
            raise RuntimeError(f"Already waiting for a message in chat {chat_id}")

        wait_message = WaitMessage(
            event=asyncio.Event(),
            from_chat=chat_id,
            wait_from=wait_from,
            is_waiting=True,
        )

        self.message_pool[chat_id] = wait_message
        message: Message | None

        try:
            message = await self.send_message(chat_id, text)
            await asyncio.wait_for(
                fut=wait_message.event.wait(),
                timeout=timeout,
            )

            return wait_message.message
        except TimeoutError:
            return None
        finally:
            if message and delete:
                await message.delete()
            self.message_pool.pop(chat_id, None)

    async def __create_bot(self):
        clientName = f"FearClient ({self.name})"
        msgs: set[Message | None] = set()
        msg = await self.send_message_wait(BOTFATHER, "/newbot", delete=True)
        msgs.add(msg)
        msg = await self.send_message_wait(BOTFATHER, clientName, delete=True)
        msgs.add(msg)
        msg = await self.send_message_wait(BOTFATHER, self.botname, delete=True)
        msgs.add(msg)

        to_delete: set[int] = set()
        for msg in msgs:
            if msg:
                to_delete.add(msg.id)

        await self.delete_messages(BOTFATHER, to_delete)
        await self.start_bot(self.botname)

        # await self.setup_bot()

    async def __get_token(self) -> str:
        to_delete: set[int] = set()
        startMessage = await self.send_message_wait(
            BOTFATHER, "/start", BOTFATHER, delete=True
        )
        tokenMessage = await self.send_message_wait(
            BOTFATHER, "/token", BOTFATHER, delete=True
        )
        to_delete.add(startMessage.id) if startMessage else to_delete.add(0)
        to_delete.add(tokenMessage.id) if tokenMessage else to_delete.add(0)
        if tokenMessage and tokenMessage.reply_markup:
            selectMessage = await self.send_message_wait(
                BOTFATHER, self.botname, BOTFATHER, delete=True
            )
            to_delete.add(selectMessage.id) if selectMessage else to_delete.add(0)
            if selectMessage and selectMessage.content == "Invalid bot selected.":
                await self.__create_bot()
                await self.delete_messages(BOTFATHER, to_delete)
                return await self.__get_token()
            else:
                if selectMessage:
                    await self.delete_messages(BOTFATHER, to_delete)
                    return selectMessage.content.split("\n")[1]
                else:
                    await self.delete_messages(BOTFATHER, to_delete)
                    raise ValueError("Cant get selectMessage")
        else:
            await self.__create_bot()
            await self.delete_messages(BOTFATHER, to_delete)
            return await self.__get_token()

    async def get_bot_token(self) -> str:

        if self.is_connected:
            return await self.__get_token()
        else:
            async with self:
                return await self.__get_token()
