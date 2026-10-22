import asyncio
import logging
from collections.abc import Callable
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

from config import config
from src.core.module.manager import ModuleInstallError, ModuleManager
helpUserCommand = Command("help", ".", "Returns all commands", ClientType.USER)
helpBotCommand = Command("help", "/", "Returns all commands", ClientType.BOT)
reloadCommand = Command("reload", ".", "Reload all modules", ClientType.USER)
furListCommand = Command("flist", ".", "List modules in FUR", ClientType.USER)
furInstallCommand = Command("fins", ".", "Install a module from FUR", ClientType.USER)
furRemoveCommand = Command("frem", ".", "Remove a FUR module", ClientType.USER)
furUpdateCommand = Command("fupd", ".", "Update a module or all FUR modules", ClientType.USER)

log = logging.getLogger(__name__)


class FearUserExtended(FearUserProtocol, Protocol):
    @property
    def me(self) -> User | None: ...


class FearClientExtended(FearClientProtocol, Protocol):
    @property
    def user(self) -> FearUserExtended: ...

    restart_message: Message | None

    def schedule_reload(
        self,
        on_success: Callable[[], None] | None = None,
        on_failure: Callable[[Exception], None] | None = None,
    ) -> None: ...


class SystemModule(FearModule):
    name: str = "System"
    version: str = "1.0.0"
    author: str = "Keva1z"

    def __init__(self, client: FearClientExtended):
        super().__init__(client)
        self.client: FearClientExtended = client
        self.add_commands(
            [
                helpUserCommand,
                helpBotCommand,
                reloadCommand,
                furListCommand,
                furInstallCommand,
                furRemoveCommand,
                furUpdateCommand,
            ]
        )

    def register(self):
        reloadCommand.add_handler(
            MessageHandler(reload_handler, reloadCommand.filter & filters.me)
        )
        furListCommand.add_handler(
            MessageHandler(fur_list_handler, furListCommand.filter & filters.me)
        )
        furInstallCommand.add_handler(
            MessageHandler(fur_install_handler, furInstallCommand.filter & filters.me)
        )
        furRemoveCommand.add_handler(
            MessageHandler(fur_remove_handler, furRemoveCommand.filter & filters.me)
        )
        furUpdateCommand.add_handler(
            MessageHandler(fur_update_handler, furUpdateCommand.filter & filters.me)
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
    fear_client.schedule_reload()


def _manager() -> ModuleManager:
    return ModuleManager(config.MODULES_DIR, config.DATA_DIR)


def _arguments(message: Message) -> list[str]:
    text = message.text or message.caption or ""
    return [str(argument) for argument in text.split()[1:]]


def _schedule_module_reload(
    fear_client: FearClientExtended,
    message: Message,
    manager: ModuleManager,
    module_ids: list[str],
) -> None:
    async def finalize(success: bool, error: Exception | None = None) -> None:
        try:
            if success:
                for module_id in module_ids:
                    await asyncio.to_thread(manager.commit, module_id)
            else:
                for module_id in reversed(module_ids):
                    await asyncio.to_thread(manager.rollback, module_id)
                log.error("FUR changes rolled back after reload failure: %s", error)
        except Exception:
            log.exception("Could not finalize FUR module reload transaction")

    def on_success() -> None:
        asyncio.create_task(finalize(True))

    def on_failure(error: Exception) -> None:
        asyncio.create_task(finalize(False, error))

    fear_client.restart_message = message
    fear_client.schedule_reload(on_success, on_failure)


async def fur_list_handler(_client: Client, message: Message) -> None:
    manager = _manager()
    try:
        packages = await asyncio.to_thread(manager.list_packages)
        installed = manager.installed()
        if not packages:
            await message.edit("В FUR пока нет доступных модулей.")
            return
        lines = ["**Fear User Repository (FUR)**"]
        for package in packages:
            state = "установлен" if package.module_id in installed else "доступен"
            lines.append(f"• `{package.module_id}` — {package.version} ({state})")
        await message.edit("\n".join(lines))
    except ModuleInstallError as exc:
        log.warning("Could not list FUR modules: %s", exc)
        await message.edit(f"Не удалось получить список FUR: {exc}")


async def fur_install_handler(client: Client, message: Message) -> None:
    args = _arguments(message)
    if len(args) != 1:
        await message.edit("Использование: `.fins <module-id>`")
        return
    fear_client = cast(FearClientExtended, cast(FearUser, client).client)
    manager = _manager()
    await message.edit(f"Устанавливаю `{args[0]}` из FUR…")
    try:
        version = await asyncio.to_thread(manager.install, args[0])
        await message.edit(
            f"Модуль `{args[0]}` версии {version} подготовлен; перезагрузка поставлена в очередь."
        )
        _schedule_module_reload(fear_client, message, manager, [args[0]])
    except (ModuleInstallError, OSError) as exc:
        log.warning("FUR install failed for %s: %s", args[0], exc)
        await message.edit(f"Ошибка установки `{args[0]}`: {exc}")


async def fur_remove_handler(client: Client, message: Message) -> None:
    args = _arguments(message)
    if len(args) != 1:
        await message.edit("Использование: `.frem <module-id>`")
        return
    fear_client = cast(FearClientExtended, cast(FearUser, client).client)
    manager = _manager()
    try:
        await asyncio.to_thread(manager.remove, args[0])
        await message.edit(f"Удаление `{args[0]}` подготовлено; перезагрузка поставлена в очередь.")
        _schedule_module_reload(fear_client, message, manager, [args[0]])
    except (ModuleInstallError, OSError) as exc:
        log.warning("FUR removal failed for %s: %s", args[0], exc)
        await message.edit(f"Ошибка удаления `{args[0]}`: {exc}")


async def fur_update_handler(client: Client, message: Message) -> None:
    args = _arguments(message)
    if len(args) > 1:
        await message.edit("Использование: `.fupd [module-id|all]`")
        return
    manager = _manager()
    try:
        installed = manager.installed()
        if args and args[0] != "all":
            module_ids = [args[0]]
        else:
            module_ids = list(installed)
        if not module_ids:
            await message.edit("Нет установленных через FUR модулей для обновления.")
            return
        fear_client = cast(FearClientExtended, cast(FearUser, client).client)
        updated: list[str] = []
        changed_ids: list[str] = []
        try:
            for module_id in module_ids:
                version = await asyncio.to_thread(manager.install, module_id, update=True)
                changed_ids.append(module_id)
                updated.append(f"`{module_id}` → {version}")
        except Exception:
            for module_id in reversed(changed_ids):
                await asyncio.to_thread(manager.rollback, module_id)
            raise
        await message.edit("Обновления подготовлены; перезагрузка поставлена в очередь:\n" + "\n".join(updated))
        _schedule_module_reload(fear_client, message, manager, changed_ids)
    except (ModuleInstallError, OSError) as exc:
        log.warning("FUR update failed: %s", exc)
        await message.edit(f"Ошибка обновления: {exc}")
