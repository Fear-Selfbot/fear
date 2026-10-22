# Fear: устройство проекта

Fear — запускаемый Python-клиент для личного Telegram-аккаунта и связанного с ним бота. Код требует Python 3.14 или новее и использует `uv`; Telegram API-клиенты предоставляет Kurigram, а `fear-module` задаёт контракт расширений.

## Запуск и жизненный цикл

`main.py` устанавливает event loop через `kurigram-utils`, создаёт `FearClient` из настроек `config.py`, вызывает `setup()`, затем передаёт два клиента в `pyrogram.compose`.

`FearClient.setup()` подключает пользовательский аккаунт, через BotFather получает токен бота, создаёт и настраивает бот-клиент, затем загружает модули. После запуска обработчик `.reload` планирует остановку двух клиентов, повторную загрузку модулей и запуск клиентов.

## Модули

Загрузчик `src/core/module/loader.py` ищет `src/modules/*/main.py`, импортирует каждый найденный файл и создаёт определённые в нём подклассы `FearModule`. Метод `register()` вызывается при загрузке. Обработчики типа `USER` ставятся на user-клиент, `BOT` — на bot-клиент, `SECRETARY` — также на bot-клиент. Каталог модулей является границей исполнения кода: его содержимое запускается с правами процесса.

Системный модуль в `src/modules/system/main.py` реализует `.help`, `/help` и `.reload`. Fear Module SDK описывает `Command`, `ClientType` и `FearModule`; подробности — в [интеграции модулей](modules.md).

## Конфигурация и данные

Обязательные переменные `.env`: `API_ID`, `API_HASH`, `PASSWORD`, `PHONE`, `NAME`. Уровень логирования задаётся `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`), по умолчанию `INFO`. Необязательные параметры прокси: `PROXY_TYPE` (`http` или `socks5`), `PROXY_HOST`, `PROXY_PORT`, `PROXY_USER`, `PROXY_PASSWORD`. Прокси выключен, когда host равен `localhost`; логин и пароль опциональны. Сессии сохраняются в `.data/sessions` (путь вычисляется относительно `config.py`); каталог `.data` исключён из Git.

Параметры конфигурации отражены в `.env.example`; неиспользуемые опции не объявляются как действующие настройки.

## Разработка и ограничения

Проверки: `python -m compileall -q main.py config.py src tests`, `uv lock --check`, `uv run --locked python -m unittest discover -s tests -v` и `ty check`. CI-конфигурации пока нет. Сетевой запуск обращается к реальному Telegram и может создавать бота через BotFather. Fear настраивает root logging; логи SDK наследуют эту конфигурацию.
