import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from io import BytesIO
from typing import TypeVar

from pyrogram import Client, types
from pyrogram.errors import FloodWait
from pyrogram.types import InputChatPhotoStatic, Message

BOTFATHER = "BotFather"
BOTFATHER_TIMEOUT = 30
BOTFATHER_ATTEMPTS = 3
FLOOD_WAIT_ATTEMPTS = 3
TOKEN_PATTERN = re.compile(r"(?m)^\d+:[A-Za-z0-9_-]+$")
NO_BOTS_PATTERN = re.compile(r"\bno bots?\b|don't have any bots", re.IGNORECASE)
T = TypeVar("T")
log = logging.getLogger(__name__)


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
        timeout: float = 30.0,
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
        sent_message: Message | None = None

        try:
            sent_message = await self.send_message(chat_id, text)
            await asyncio.wait_for(
                fut=wait_message.event.wait(),
                timeout=timeout,
            )

            return wait_message.message
        except TimeoutError:
            return None
        finally:
            try:
                if sent_message and delete:
                    await sent_message.delete()
            except Exception:
                log.exception("Could not delete the outgoing message after waiting")
            finally:
                self.message_pool.pop(chat_id, None)

    async def _create_bot(self) -> None:
        client_name = f"FearClient ({self.name})"
        replies: list[Message] = []
        try:
            for text in ("/newbot", client_name, self.botname):
                reply = await self.send_message_wait(
                    BOTFATHER,
                    text,
                    wait_from=BOTFATHER,
                    delete=True,
                    timeout=BOTFATHER_TIMEOUT,
                )
                if reply is None:
                    raise TimeoutError(f"BotFather did not answer {text!r}")
                replies.append(reply)

            await self.start_bot(self.botname)
        finally:
            await self._delete_botfather_messages(replies)

    async def _delete_botfather_messages(self, messages: list[Message]) -> None:
        message_ids = [message.id for message in messages if message.id]
        if not message_ids:
            return
        try:
            await self.delete_messages(BOTFATHER, message_ids)
        except Exception:
            # Cleanup must not hide the BotFather error or a successfully parsed token.
            log.exception("Could not remove BotFather conversation messages")

    async def _send_message_waiting_for_botfather(self, text: str) -> Message | None:
        return await self.send_message_wait(
            BOTFATHER,
            text,
            wait_from=BOTFATHER,
            delete=True,
            timeout=BOTFATHER_TIMEOUT,
        )

    async def _parse_bot_token(self, message: Message) -> str:
        content = message.content or ""
        match = TOKEN_PATTERN.search(content)
        if match is None:
            raise ValueError("BotFather response did not contain a valid bot token")
        return match.group(0)

    async def _get_token(self) -> str:
        created_bot = False
        for attempt in range(BOTFATHER_ATTEMPTS):
            replies: list[Message] = []
            try:
                start_reply = await self._send_message_waiting_for_botfather("/start")
                if start_reply is None:
                    raise TimeoutError("BotFather timed out while starting the chat")
                replies.append(start_reply)

                token_prompt = await self._send_message_waiting_for_botfather("/token")
                if token_prompt is None:
                    raise TimeoutError("BotFather timed out while listing bot tokens")
                replies.append(token_prompt)

                if not token_prompt.reply_markup:
                    if not NO_BOTS_PATTERN.search(token_prompt.content or ""):
                        raise RuntimeError(
                            "BotFather returned an unrecognized response to /token"
                        )
                    if created_bot:
                        raise RuntimeError(
                            "BotFather did not list the newly created bot"
                        )
                    await self._create_bot()
                    created_bot = True
                    continue

                selection = await self._send_message_waiting_for_botfather(self.botname)
                if selection is None:
                    raise TimeoutError("BotFather timed out while selecting the bot")
                replies.append(selection)

                if "invalid bot selected" in (selection.content or "").casefold():
                    if created_bot:
                        raise RuntimeError("BotFather rejected the newly created bot")
                    await self._create_bot()
                    created_bot = True
                    continue

                return await self._parse_bot_token(selection)
            finally:
                await self._delete_botfather_messages(replies)

        raise RuntimeError(
            f"Could not retrieve a bot token after {BOTFATHER_ATTEMPTS} attempts"
        )

    async def get_bot_token(self) -> str:

        if self.is_connected:
            return await self._get_token()
        else:
            async with self:
                return await self._get_token()

    async def _with_flood_wait_retry(
        self, operation: Callable[[], Awaitable[T]], label: str
    ) -> T:
        for attempt in range(FLOOD_WAIT_ATTEMPTS):
            try:
                return await operation()
            except FloodWait as error:
                if attempt + 1 == FLOOD_WAIT_ATTEMPTS:
                    raise
                value = error.value
                if isinstance(value, int):
                    delay = value
                elif isinstance(value, str):
                    try:
                        delay = int(value)
                    except ValueError:
                        delay = 1
                else:
                    delay = 1
                delay = max(1, delay)
                log.warning("FloodWait during %s; retrying in %s seconds", label, delay)
                await asyncio.sleep(delay)
        raise RuntimeError(f"{label} did not complete")

    async def setup_bot_settings(self, bot: Client):
        if not self.is_connected or not bot.is_connected:
            return

        operations = (
            ("profile photo", self.__set_bot_photo),
            ("bot name", self.__set_name),
            ("bot description", self.__set_description),
            ("bot short description", self.__set_about),
        )
        for label, operation in operations:
            await self._with_flood_wait_retry(lambda: operation(bot), label)

    async def __set_bot_photo(self, bot: Client):
        if not self.me or not bot.me:
            return

        if not self.me.photo:
            return

        my_photo = await self.download_media(self.me.photo, in_memory=True)
        if isinstance(my_photo, BytesIO):
            my_photo.seek(0)
            await bot.set_profile_photo(InputChatPhotoStatic(my_photo))

    async def __set_name(self, bot: Client):
        if not self.me or not bot.me:
            return

        if not self.me.username:
            return

        name = f"FearClient ({self.me.username})"
        if bot.me.full_name != name:
            await bot.set_bot_name(name)

    async def __set_description(self, bot: Client):
        if not self.me or not bot.me:
            return

        if not self.me.username:
            return

        description = """This is bot controlled by "Fear" selfbot"""

        if await bot.get_bot_info_description() != description:
            await bot.set_bot_info_description(description)

    async def __set_about(self, bot: Client):
        if not self.me or not bot.me:
            return

        if not self.me.username:
            return

        description = """This is bot controlled by "Fear" selfbot"""

        if await bot.get_bot_info_short_description() != description:
            await bot.set_bot_info_short_description(description)
