import asyncio
import unittest
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from src.core.client import FearClient


class FakeClient:
    def __init__(self, connected=True, fail_on=None):
        self.is_connected = connected
        self.handlers = set()
        self.fail_on = fail_on

    def add_handler(self, handler):
        if handler == self.fail_on:
            raise RuntimeError("handler registration failed")
        self.handlers.add(handler)

    def remove_handler(self, handler):
        self.handlers.discard(handler)


class FakeModule:
    user_handlers = ["old-user"]
    bot_handlers = ["old-bot"]

    def get_handlers(self, client_type):
        return []


class NewModule:
    user_handlers = ["new-user"]
    bot_handlers = ["new-bot"]

    def get_handlers(self, client_type):
        return []


class ModuleReloadTests(unittest.TestCase):
    def make_client(self, connected=True, fail_on=None):
        client = cast(Any, FearClient.__new__(FearClient))
        client._user = FakeClient(connected, fail_on)
        client._bot = FakeClient(connected)
        client._loaded_modules = [FakeModule()]
        client._user.handlers.update(FakeModule.user_handlers)
        client._bot.handlers.update(FakeModule.bot_handlers)
        return client

    def test_load_failure_preserves_active_handlers(self):
        client = self.make_client()
        loader = type("Loader", (), {"load": lambda _self, _client: (_ for _ in ()).throw(ValueError("bad module"))})

        with patch("src.core.client.ModuleLoader", return_value=loader()):
            with self.assertRaisesRegex(ValueError, "bad module"):
                client.load_modules()

        self.assertEqual(client._user.handlers, {"old-user"})
        self.assertEqual(client._bot.handlers, {"old-bot"})
        self.assertIsInstance(client.modules[0], FakeModule)

    def test_registration_failure_restores_previous_module_handlers(self):
        client = self.make_client(fail_on="new-user")
        loader = type("Loader", (), {"load": lambda _self, _client: [NewModule()]})

        with patch("src.core.client.ModuleLoader", return_value=loader()):
            with self.assertRaisesRegex(RuntimeError, "registration failed"):
                client.load_modules()

        self.assertEqual(client._user.handlers, {"old-user"})
        self.assertEqual(client._bot.handlers, {"old-bot"})
        self.assertIsInstance(client.modules[0], FakeModule)

    def test_registration_failure_after_stop_restores_previous_module_handlers(self):
        client = self.make_client(connected=False, fail_on="new-user")
        client._user.handlers.clear()
        client._bot.handlers.clear()
        loader = type("Loader", (), {"load": lambda _self, _client: [NewModule()]})

        with patch("src.core.client.ModuleLoader", return_value=loader()):
            with self.assertRaisesRegex(RuntimeError, "registration failed"):
                client.load_modules()

        self.assertEqual(client._user.handlers, {"old-user"})
        self.assertEqual(client._bot.handlers, {"old-bot"})

    def test_reload_failure_after_stop_restores_handlers(self):
        client = self.make_client(connected=False)
        client._user.handlers.clear()
        client._bot.handlers.clear()
        loader = type("Loader", (), {"load": lambda _self, _client: (_ for _ in ()).throw(ValueError("bad module"))})

        with patch("src.core.client.ModuleLoader", return_value=loader()):
            with self.assertRaisesRegex(ValueError, "bad module"):
                client.load_modules()

        self.assertEqual(client._user.handlers, {"old-user"})
        self.assertEqual(client._bot.handlers, {"old-bot"})


class ScheduledReloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduled_reload_coalesces_requests_and_calls_success_hooks(self):
        client = cast(Any, FearClient.__new__(FearClient))
        client._reload_callbacks = []
        client._reload_task = None
        completed = []
        async def restart():
            client._finish_reload_callbacks()

        with patch.object(client, "restart_clients", new=AsyncMock(side_effect=restart)) as task:
            client.schedule_reload(lambda: completed.append("first"))
            client.schedule_reload(lambda: completed.append("second"))
            await asyncio.sleep(0)
            await cast(asyncio.Task[None], client._reload_task)

        task.assert_awaited_once()
        self.assertEqual(completed, ["first", "second"])

    async def test_scheduled_reload_calls_failure_hook(self):
        client = cast(Any, FearClient.__new__(FearClient))
        client._reload_callbacks = []
        client._reload_task = None
        failures = []
        error = RuntimeError("reload failed")

        async def restart():
            client._finish_reload_callbacks(error)

        with patch.object(client, "restart_clients", new=AsyncMock(side_effect=restart)) as task:
            client.schedule_reload(on_failure=failures.append)
            await asyncio.sleep(0)
            await cast(asyncio.Task[None], client._reload_task)

        task.assert_awaited_once()
        self.assertEqual(failures, [error])

    async def test_reload_requested_mid_cycle_runs_after_current_reload(self):
        client = cast(Any, FearClient.__new__(FearClient))
        client._reload_callbacks = []
        client._queued_reload_callbacks = []
        client._reload_task = None
        completed = []
        call_count = 0

        async def restart():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                client.schedule_reload(lambda: completed.append("queued"))
            client._finish_reload_callbacks()
            client._schedule_followup_reload()

        with patch.object(client, "restart_clients", new=AsyncMock(side_effect=restart)):
            client.schedule_reload(lambda: completed.append("current"))
            await asyncio.sleep(0)
            await cast(asyncio.Task[None], client._reload_task)
            await asyncio.sleep(0)
            await cast(asyncio.Task[None], client._reload_task)

        self.assertEqual(call_count, 2)
        self.assertEqual(completed, ["current", "queued"])


if __name__ == "__main__":
    unittest.main()
