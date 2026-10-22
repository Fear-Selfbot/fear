# Интеграция модулей Fear

## Где размещать модуль

Создайте каталог `src/modules/<module_name>/` и файл `main.py`. Загрузчик автоматически импортирует `main.py`, находит объявленные в нём подклассы `fear_module.FearModule`, создаёт экземпляры с `FearClient` и вызывает `register()`.

```python
from fear_module import Command, FearModule
from pyrogram.handlers import MessageHandler

ping = Command("ping", ".", "Проверка связи")

async def ping_handler(client, message):
    await message.edit("pong")

class PingModule(FearModule):
    name = "Ping"

    def register(self):
        ping.add_handler(MessageHandler(ping_handler, ping.filter))
        self.add_commands(ping)
```

Команда должна быть добавлена экземпляру модуля через `add_commands`; обработчики команды добавляются в сам `Command`. Общие обработчики добавляются через `add_handlers`. Для выбора клиента укажите `client_type` у `Command` или модуля: `ClientType.USER`, `BOT` или `SECRETARY`. Fear подключает обработчики `SECRETARY` к bot-клиенту.

## Перезагрузка и безопасность

`.reload` останавливает клиентов, повторно импортирует Python-модули и регистрирует обработчики заново. Импортируемый код выполняется с правами процесса Fear, поэтому размещайте там только проверенные модули. Избегайте внешних побочных эффектов на уровне импорта и повторно используемых глобальных изменяемых объектов: `register()` вызывается при каждой перезагрузке.

SDK предоставляет `Command`, `ClientType`, `FearModule`, типы клиентов и протокол клиента. `FearClientProtocol` описывает хост; экспортируемый `FearClient` сохранён как каркас обратной совместимости и выбрасывает `NotImplementedError` для не реализованных им операций. Реальная оркестрация находится в приложении Fear.
