import asyncio

from dispyro import Dispatcher
from pyrogram import Client, filters
from pyrogram.enums import ClientPlatform
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from config import config

from .handlers import get_routers
from .handlers.waiter import waitHandler
from .types import WaitMessage


def get_sessions() -> list[str]:
    return [f.stem for f in config.SESSIONS_DIR.glob("*.session")]


client_kwargs = {
    "proxy": config.proxy.http if config.proxy.HOST != "localhost" else None,
    "client_platform": ClientPlatform.DESKTOP,
    "device_model": "Desktop",
    "system_version": "Windows 11 x64",
    "app_version": "7.2.9 x64",
    "workdir": str(config.SESSIONS_DIR),
}

bot_kwargs = {
    "proxy": config.proxy.http if config.proxy.HOST != "localhost" else None,
    "workdir": str(config.SESSIONS_DIR),
}


class FearClient(Client):
    def __init__(
        self,
        name: str,
        api_id: int | None = None,
        api_hash: str | None = None,
        phone_number: str | None = None,
        password: str | None = None,
        plugins: dict | None = None,
        **kwargs,
    ):
        self.waitingMessage: WaitMessage | None = None

        super().__init__(
            name=name,
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone_number,
            password=password,
            plugins=plugins,
            **kwargs,
        )

        self.botFather = "BotFather"
        self.botName = f"@FearClient{self.name}_bot"

    async def send_and_wait_message(
        self,
        chatId: str | int,
        text: str,
        waitFrom: str | int | None = None,
        timeout: int = 30,
    ) -> Message | None:
        try:
            self.waitingMessage = WaitMessage(
                event=asyncio.Event(),
                fromChat=chatId,
                waitFrom=waitFrom,
                is_waiting=True,
            )
            await self.send_message(chatId, text)
            await asyncio.wait_for(
                fut=self.waitingMessage.event.wait(), timeout=timeout
            )

            return self.waitingMessage.message
        except TimeoutError:
            return None
        finally:
            self.waitingMessage = None

    async def setup_bot(self):
        if not self.me:
            return

        h = MessageHandler(waitHandler, filters.chat(self.botFather))
        self.add_handler(h)

        description = """This is bot controlled by "Fear" selfbot"""

        if self.me.username:
            await self.send_and_wait_message(self.botFather, "/setname")
            await self.send_and_wait_message(self.botFather, self.botName)
            await self.send_and_wait_message(
                self.botFather, f"FearClient ({self.me.username})"
            )

        await asyncio.sleep(0.5)

        # Setup photo
        if self.me.photo:
            await self.send_and_wait_message(self.botFather, "/setuserpic")
            await self.send_and_wait_message(self.botFather, self.botName)
            await self.send_cached_media(self.botFather, self.me.photo.big_file_id)

        await asyncio.sleep(0.5)

        # Setup description
        await self.send_and_wait_message(self.botFather, "/setdescription")
        await self.send_and_wait_message(self.botFather, self.botName)
        await self.send_and_wait_message(self.botFather, description)

        await asyncio.sleep(0.5)

        # Setup about
        await self.send_and_wait_message(self.botFather, "/setabouttext")
        await self.send_and_wait_message(self.botFather, self.botName)
        await self.send_and_wait_message(self.botFather, description)

        # Setup join groups policy
        await self.send_and_wait_message(self.botFather, "/setjoingroups")
        await self.send_and_wait_message(self.botFather, self.botName)
        await self.send_and_wait_message(self.botFather, "Disable")

        self.remove_handler(h)

    async def __create_bot(self, chatId: str, name: str):
        clientName = f"FearClient ({self.name})"
        await self.send_and_wait_message(chatId, "/newbot")
        await self.send_and_wait_message(chatId, clientName)
        await self.send_and_wait_message(chatId, name)

        await self.setup_bot()

    async def __get_token(self, chatId: str, name: str) -> str:
        tokenMessage = await self.send_and_wait_message(chatId, "/token")
        if tokenMessage and tokenMessage.reply_markup:
            selectMessage = await self.send_and_wait_message(chatId, f"{name}")
            if selectMessage and selectMessage.content == "Invalid bot selected.":
                await self.__create_bot(chatId, name)
                return await self.__get_token(chatId, name)
            else:
                if selectMessage:
                    return selectMessage.content.split("\n")[1]
                else:
                    raise ValueError("Cant get selectMessage")
        else:
            await self.__create_bot(chatId, name)
            return await self.__get_token(chatId, name)

    async def get_bot_token(self) -> str:
        token = ""

        async with self:
            await self.send_and_wait_message(self.botFather, "/start")
            token = await self.__get_token(self.botFather, self.botName)

        return token


class FearBot(Client):
    def __init__(
        self,
        name: str,
        bot_token: str | None = None,
        api_id: int | None = None,
        api_hash: str | None = None,
        **kwargs,
    ):
        super().__init__(
            name=name, api_id=api_id, api_hash=api_hash, bot_token=bot_token, **kwargs
        )


class FearCore:
    def __init__(self):
        pass

    async def start(self) -> None:
        await self.__load_sessions()

    async def __create_first_session(self) -> str:
        app = FearClient(
            name=config.NAME,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE,
            password=config.PASSWORD,
            plugins=None,
            **client_kwargs,
        )

        await app.start()
        await app.stop()

        token = await app.get_bot_token()
        botName = f"{config.NAME}_bot"

        bot = FearBot(
            name=botName,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=token,
            **bot_kwargs,
        )

        await bot.start()
        await bot.stop()

        return config.NAME

    async def __create_clients(self, names: list[str]) -> list[Client]:

        clients: list[Client] = []

        for name in names:
            if name.endswith("_bot"):
                continue

            plugins = dict(root="src/client/handlers/plugins")  # noqa: C408
            client = FearClient(
                name=name,
                api_id=None,
                api_hash=None,
                phone_number=None,
                password=None,
                plugins=plugins,
                **client_kwargs,
            )

            await client.start()
            await client.setup_bot()
            await client.stop()

            bot = FearBot(
                f"{name}_bot",
                api_id=None,
                api_hash=None,
                bot_token=None,
                **bot_kwargs,
            )

            clients.append(client)
            clients.append(bot)

        return clients

    async def __load_sessions(self) -> None:

        files = get_sessions()

        if not files:
            files.append(await self.__create_first_session())

        clients = await self.__create_clients(files)
        dp = Dispatcher(*clients, disable_fsm=True)

        dp.add_routers(*get_routers())

        await dp.start()
