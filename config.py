"""Validated environment settings, instantiated explicitly during startup."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from pyrogram.connection import HTTPProxy, SOCKS5Proxy


class PROXYSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="PROXY_", extra="ignore"
    )

    HOST: str = "localhost"
    PORT: int = 8080
    USER: str = "user"
    PASSWORD: str = "password"

    @property
    def http(self) -> HTTPProxy:
        from pyrogram.connection import HTTPProxy

        return HTTPProxy(
            hostname=self.HOST,
            port=self.PORT,
            username=self.USER,
            password=self.PASSWORD,
        )

    @property
    def socks5(self) -> SOCKS5Proxy:
        from pyrogram.connection import SOCKS5Proxy

        return SOCKS5Proxy(
            hostname=self.HOST,
            port=self.PORT,
            username=self.USER,
            password=self.PASSWORD,
        )

    @property
    def HTTP(self) -> HTTPProxy:
        """Backward-compatible alias for the HTTP proxy."""
        return self.http

    @property
    def SOCKS5(self) -> SOCKS5Proxy:
        """Backward-compatible alias for the SOCKS5 proxy."""
        return self.socks5


class Settings(BaseSettings):
    """Application settings, loaded only when explicitly instantiated."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    API_ID: int
    API_HASH: str
    PASSWORD: str
    PHONE: str
    NAME: str
    SUPERADMIN_IDS: list[int] = Field(default_factory=list)

    DATA_DIR: Path = Path(__file__).parent / ".data"
    SESSIONS_DIR: Path = DATA_DIR / "sessions"
    HANDLERS_DIR: Path = Path(__file__).parent / "src" / "client" / "handlers"
    MODULES_DIR: Path = Path(__file__).parent / "src" / "modules"

    # Load PROXY_* only when Settings is created, not when this module is imported.
    proxy: PROXYSettings = Field(default_factory=PROXYSettings)


config = Settings()

config.SESSIONS_DIR.mkdir(exist_ok=True, parents=True)

# if not config.DATA_DIR.exists():
#     os.mkdir(config.DATA_DIR)

# if not config.SESSIONS_DIR.exists():
#     os.mkdir(config.SESSIONS_DIR)
