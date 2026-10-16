from config import config


def get_sessions() -> list[str]:
    return [
        f.stem
        for f in config.SESSIONS_DIR.glob("*.session")
        if not f.stem.endswith("_bot")
    ]
