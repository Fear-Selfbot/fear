from typing import cast

from fear_module import (
    ClientType,
    Command,
    FearClient,
    FearModule,
    FearUser,
)
from pyrogram import Client, filters, types
from pyrogram.handlers import (
    BusinessMessageHandler,
    CallbackQueryHandler,
    MessageHandler,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

testCommand = Command("test", ".", "Test command")
testBusinessCommand = Command(
    "testb",
    ".",
    "Test business message",
    ClientType.SECRETARY,
)


class TestModule(FearModule):
    name: str = "Test"
    version: str = "1.0.0"
    author: str = "Keva1z"

    def __init__(self, client: FearClient):
        super().__init__(client)
        self.client: FearClient = client
        self.add_commands(
            [
                testCommand,
                testBusinessCommand,
            ]
        )

    def register(self):
        testCommand.add_handler(
            MessageHandler(test_handler, testCommand.filter & filters.me)
        )
        testBusinessCommand.add_handler(
            BusinessMessageHandler(
                test_business, testBusinessCommand.filter & filters.me
            )
        )
        testBusinessCommand.add_handler(
            CallbackQueryHandler(test_business_callback, filters.regex("test"))
        )


async def test_handler(client: Client, message: types.Message):
    client = cast(FearUser, client)

    if message.chat:
        await message.edit(f"{message.chat.type}")


kb = InlineKeyboardMarkup([[InlineKeyboardButton("Тест", callback_data="test")]])


async def test_business(client: Client, message: types.Message):
    await message.edit("Тестовая бизнес кнопка", reply_markup=kb)


async def test_business_callback(client: Client, callback: types.CallbackQuery):
    await callback.answer("Нажал!")
    if callback.message:
        await callback.message.answer("Ты нажал!")
