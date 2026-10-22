import unittest
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any, cast

from pyrogram.types import Message

from src.core.mixins.user import UserMethods


class FakeMessage:
    id = 42

    def __init__(self):
        self.deleted = False

    async def delete(self):
        self.deleted = True


class FailingDeleteMessage(FakeMessage):
    async def delete(self):
        raise RuntimeError("delete failed")


class FakeUser(UserMethods):
    def __init__(self, send_result=None, send_error=None):
        self.message_pool = {}
        self.name = "test"
        self.send_result = send_result or FakeMessage()
        self.send_error = send_error
        self.botfather_replies: list[Message | None] = []
        self.botfather_calls: list[str] = []
        self.bot_create_count = 0

    async def send_message(self, chat_id: Any, text: Any, *args: Any, **kwargs: Any) -> Message | None:
        if self.send_error:
            raise self.send_error
        return cast(Message, self.send_result)

    async def _send_message_waiting_for_botfather(self, text: str) -> Message | None:
        self.botfather_calls.append(text)
        return self.botfather_replies.pop(0)

    async def _create_bot(self) -> None:
        self.bot_create_count += 1

    async def delete_messages(
        self,
        chat_id: int | str,
        message_ids: int | Iterable[int],
        revoke: bool = True,
        is_scheduled: bool | None = None,
    ) -> int:
        return 0


class SendMessageWaitTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_error_is_preserved_and_pool_is_cleared(self):
        error = RuntimeError("network unavailable")
        user = FakeUser(send_error=error)

        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            await user.send_message_wait("chat", "hello")

        self.assertEqual(user.message_pool, {})

    async def test_timeout_deletes_outgoing_message_and_clears_pool(self):
        sent = FakeMessage()
        user = FakeUser(send_result=sent)

        result = await user.send_message_wait("chat", "hello", delete=True, timeout=0.01)

        self.assertIsNone(result)
        self.assertTrue(sent.deleted)
        self.assertEqual(user.message_pool, {})

    async def test_delete_error_does_not_leave_pool_entry_or_mask_timeout(self):
        user = FakeUser(send_result=FailingDeleteMessage())

        with self.assertLogs("src.core.mixins.user", level="ERROR"):
            result = await user.send_message_wait(
                "chat", "hello", delete=True, timeout=0.01
            )

        self.assertIsNone(result)
        self.assertEqual(user.message_pool, {})

    async def test_botfather_timeout_fails_without_creating_bot_or_recursing(self):
        user = FakeUser()
        user.botfather_replies = [None]

        with self.assertRaisesRegex(TimeoutError, "timed out"):
            await user._get_token()

        self.assertEqual(user.botfather_calls, ["/start"])
        self.assertEqual(user.bot_create_count, 0)

    async def test_token_parser_rejects_unexpected_botfather_response(self):
        user = FakeUser()

        with self.assertRaisesRegex(ValueError, "valid bot token"):
            await user._parse_bot_token(
                cast(Message, SimpleNamespace(content="Unexpected response"))
            )

    async def test_unrecognized_token_list_response_does_not_create_a_bot(self):
        user = FakeUser()
        replies = [
            SimpleNamespace(id=1, content="Started", reply_markup=None),
            SimpleNamespace(id=2, content="Temporary error", reply_markup=None),
        ]
        user.botfather_replies = [cast(Message, reply) for reply in replies]

        with self.assertRaisesRegex(RuntimeError, "unrecognized response"):
            await user._get_token()

        self.assertEqual(user.botfather_calls, ["/start", "/token"])
        self.assertEqual(user.bot_create_count, 0)

    async def test_known_empty_token_list_creates_once_then_returns_token(self):
        user = FakeUser()
        replies = [
            SimpleNamespace(id=1, content="Started", reply_markup=None),
            SimpleNamespace(id=2, content="You have no bots yet", reply_markup=None),
            SimpleNamespace(id=3, content="Started", reply_markup=None),
            SimpleNamespace(id=4, content="Select a bot", reply_markup=object()),
            SimpleNamespace(id=5, content="12345:abc_DEF-456", reply_markup=None),
        ]
        user.botfather_replies = [cast(Message, reply) for reply in replies]

        token = await user._get_token()

        self.assertEqual(token, "12345:abc_DEF-456")
        self.assertEqual(user.bot_create_count, 1)
        self.assertEqual(
            user.botfather_calls,
            ["/start", "/token", "/start", "/token", user.botname],
        )


if __name__ == "__main__":
    unittest.main()
