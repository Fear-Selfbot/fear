# Модули Fear и FUR

## Формат и загрузка

Загрузчик ищет `modules/<id>/main.py`, импортирует `modules.<id>.main`, находит локальные подклассы `fear_module.FearModule`, создаёт их с host client и вызывает `register()`. Встроенные системные команды живут в `modules/system/main.py`. Устанавливаемые из FUR модули находятся в том же каталоге; их зависимости размещаются в `.data/module-deps/<id>/`.

```python
from fear_module import Command, FearModule
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message


class PingModule(FearModule):
    name = "Ping"
    version = "1.0.0"

    def register(self) -> None:
        command = Command("ping", ".", "Check that Fear is responding")

        async def ping_handler(_client, message: Message) -> None:
            await message.edit("pong")

        command.add_handler(
            MessageHandler(ping_handler, command.filter & filters.me)
        )
        self.add_commands(command)
```

`Command` выбирает клиент через `ClientType.USER`, `BOT` или `SECRETARY`; secretary handlers подключаются к bot client. `.reload` перезапускает Telegram-клиенты и повторно загружает все модули. FUR-команды применяют установку/удаление без перезапуска клиентов.

## Команды System для FUR

- `.flist` — получить список пакетов и статус установки.
- `.fins <module-id>` — установить пакет из фиксированного FUR.
- `.frem <module-id>` — удалить установленный пакет.
- `.fupd <module-id>` — обновить один установленный пакет.
- `.fupd` или `.fupd all` — обновить все установленные FUR-пакеты.

Команды зарегистрированы с `filters.me` и принимаются только от текущего аккаунта user-клиента. После подготовки изменений они вызывают общий `schedule_reload()`; работа с Telegram-клиентами и повторная загрузка модулей выполняются в общем restart-flow, а файлы фиксируются только после успешной загрузки. Имя не является URL или pip specifier.

Установка проверяет идентификатор, версию из каталога и манифеста, SHA-256 архива, ZIP paths, отсутствие symlinks и лимиты размера; файлы сначала распаковываются во временный скрытый каталог. Неудачная активация восстанавливает прежние файлы и состояние установленных модулей. ZIP ограничен 20 MiB, распакованное содержимое — 50 MiB.

## Формат FUR-пакета

FUR — фиксированный репозиторий `Fear-Selfbot/fear-repository`; каталог читается из `registry.json` в ветке `main`. Каталог содержит `modules`, элементы имеют поля:

```json
{
  "id": "hello",
  "version": "1.0.0",
  "archive": "packages/hello-1.0.0.zip",
  "sha256": "<64 hex characters>"
}
```

ZIP содержит в корне `fear-module.json`, `main.py` и опциональный hash-pinned `requirements.lock` (формат pip requirements). Манифест обязан совпадать по `id` и `version`; остальные поля манифеста пока служат метаданными и не проверяются совместимостью загрузчика. README и рабочий пример находятся в репозитории [FUR](https://github.com/Fear-Selfbot/fear-repository).

Зависимости устанавливаются вызовом `uv pip install --require-hashes --only-binary :all: --target ... -r requirements.lock` вне asyncio event loop. Используйте точные версии, хеши и wheel-пакеты; соберите lock через `uv pip compile --generate-hashes`. Зависимости разделены по каталогам, но Python-процесс общий: `sys.modules` глобален, поэтому две версии библиотеки с одинаковым import name не изолированы. Уже импортированную версию нельзя надёжно выгрузить или заменить на лету. Удаление модуля снимает его handlers, но не очищает произвольные побочные эффекты или импортированные библиотеки; такие изменения могут потребовать полного перезапуска процесса.

## Граница доверия

SHA-256 в `registry.json` позволяет заметить несоответствие архива каталогу, но репозиторий контролирует и архив, и digest; это не независимая цифровая подпись. Модуль — доверенный Python-код с правами процесса Fear: он может обращаться к сессиям, окружению, сети и файловой системе. Установка зависимостей также требует доверия к издателю. Устанавливайте только проверенные пакеты. Для недоверенных или конфликтующих модулей нужна отдельная процессная песочница, которой текущая архитектура не предоставляет.
