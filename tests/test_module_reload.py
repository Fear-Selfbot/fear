import unittest
from typing import Any, cast
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
