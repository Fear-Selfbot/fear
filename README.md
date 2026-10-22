# Fear Client

Fear is a Python 3.14+ Telegram client that runs a user client and a linked bot client. It loads trusted Python modules from `src/modules/<name>/main.py`; the module API is provided by the separate [Fear Module SDK](https://github.com/Fear-Selfbot/fear-module).

## Setup

1. Install Python 3.14+ and [uv](https://docs.astral.sh/uv/).
2. Copy `.env.example` to `.env` and set `API_ID`, `API_HASH`, `PASSWORD`, `PHONE`, and `NAME`.
3. Install the locked project environment with `uv sync --locked`.
4. Start the client with `uv run --locked python main.py`.

On startup Fear talks to BotFather to find or create the linked bot. Telegram credentials and session files in `.data/sessions` are sensitive; never commit them or install untrusted modules. See [architecture](docs/architecture.md), [module authoring](docs/modules.md), [review status](docs/code-review.md), and the [module format and dependency installation proposal](docs/module-format-proposal.md).

## Development checks

```sh
uv run --locked python -m unittest discover -s tests -v
uv lock --check
```
