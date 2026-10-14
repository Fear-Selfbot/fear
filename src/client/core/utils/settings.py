from pyrogram.enums import ClientPlatform

from config import config


def get_settings(plugins_path: str | None = None):
    plugins = dict(root=plugins_path) if plugins_path else None
    return {
        "plugins": plugins,
        "proxy": config.proxy.http if config.proxy.HOST != "localhost" else None,
        "client_platform": ClientPlatform.DESKTOP,
        "device_model": "Desktop",
        "system_version": "Windows 11 x64",
        "app_version": "7.2.9 x64",
        "workdir": str(config.SESSIONS_DIR),
    }
