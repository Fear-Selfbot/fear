"""Install Fear modules from the public Fear User Repository (FUR)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

log = logging.getLogger(__name__)
_MANAGER_OPERATION_LOCK = threading.RLock()
_ACTIVE_MODULE_CHANGES: set[str] = set()

FUR_REGISTRY_URL = (
    "https://raw.githubusercontent.com/Fear-Selfbot/fear-repository/main/registry.json"
)
FUR_RAW_ROOT = "https://raw.githubusercontent.com/Fear-Selfbot/fear-repository/main/"
MAX_ARCHIVE_SIZE = 20 * 1024 * 1024
MAX_EXPANDED_SIZE = 50 * 1024 * 1024
MODULE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ModuleInstallError(Exception):
    """An expected module manager error that is safe to report to Telegram."""


@dataclass(frozen=True)
class Package:
    module_id: str
    version: str
    archive: str
    sha256: str


class ModuleManager:
    def __init__(self, modules_dir: Path, data_dir: Path):
        self.modules_dir = modules_dir.resolve()
        self.data_dir = data_dir.resolve()
        self.deps_dir = self.data_dir / "module-deps"
        self.state_file = self.data_dir / "fur-installed.json"
        self._pending: dict[str, tuple[bool, bool, dict[str, str], bool]] = {}

    def _fetch(self, url: str, limit: int) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Fear-FUR-Module-Manager/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise ModuleInstallError(f"FUR вернул HTTP {response.status}")
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > limit:
                            raise ModuleInstallError("Ответ превышает допустимый размер")
                    except ValueError as exc:
                        raise ModuleInstallError("Некорректный Content-Length от FUR") from exc
                data = response.read(limit + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModuleInstallError(f"Не удалось загрузить пакет из FUR: {exc}") from exc
        if len(data) > limit:
            raise ModuleInstallError("Ответ превышает допустимый размер")
        return data

    def _registry(self) -> dict[str, Package]:
        try:
            raw = json.loads(self._fetch(FUR_REGISTRY_URL, 1_000_000))
            entries = raw["modules"]
            if not isinstance(entries, list):
                raise ValueError("modules must be a list")
            result: dict[str, Package] = {}
            for entry in entries:
                module_id = entry["id"]
                archive = entry["archive"]
                version = entry["version"]
                digest = entry["sha256"]
                if not isinstance(module_id, str) or not MODULE_ID_RE.fullmatch(module_id):
                    raise ValueError("invalid module id")
                if not isinstance(version, str) or not version:
                    raise ValueError("invalid module version")
                if (
                    not isinstance(archive, str)
                    or archive.startswith("/")
                    or ".." in PurePosixPath(archive).parts
                    or not archive.endswith(".zip")
                ):
                    raise ValueError("invalid package archive path")
                if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
                    raise ValueError("invalid package SHA-256")
                if module_id in result:
                    raise ValueError(f"duplicate package id: {module_id}")
                result[module_id] = Package(module_id, version, archive, digest.lower())
            return result
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModuleInstallError(f"Некорректный каталог FUR: {exc}") from exc

    def list_packages(self) -> list[Package]:
        return sorted(self._registry().values(), key=lambda item: item.module_id)

    def installed(self) -> dict[str, str]:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            raise ModuleInstallError(f"Не удалось прочитать список модулей: {exc}") from exc
        if not isinstance(state, dict):
            raise ModuleInstallError("Файл установленных модулей повреждён")
        return {str(key): str(value) for key, value in state.items()}

    def _write_state(self, state: dict[str, str]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.state_file)

    def _safe_extract(self, archive_bytes: bytes, destination: Path, package: Package) -> None:
        if hashlib.sha256(archive_bytes).hexdigest() != package.sha256:
            raise ModuleInstallError("SHA-256 архива не совпадает с каталогом FUR")
        total = 0
        with tempfile.NamedTemporaryFile(suffix=".zip") as archive_file:
            archive_file.write(archive_bytes)
            archive_file.flush()
            try:
                with zipfile.ZipFile(archive_file.name) as archive:
                    for info in archive.infolist():
                        member = PurePosixPath(info.filename)
                        if member.is_absolute() or ".." in member.parts:
                            raise ModuleInstallError("Архив содержит небезопасный путь")
                        mode = info.external_attr >> 16
                        if mode & 0o170000 == 0o120000:
                            raise ModuleInstallError("Символические ссылки в архиве запрещены")
                        total += info.file_size
                        if total > MAX_EXPANDED_SIZE:
                            raise ModuleInstallError("Распакованный модуль слишком велик")
                    archive.extractall(destination)
            except zipfile.BadZipFile as exc:
                raise ModuleInstallError("Файл пакета не является корректным ZIP") from exc

        candidates = [destination]
        candidates.extend(path for path in destination.iterdir() if path.is_dir())
        package_root = next(
            (path for path in candidates if (path / "main.py").is_file()), None
        )
        if package_root is None:
            raise ModuleInstallError("В архиве не найден main.py")
        manifest_path = package_root / "fear-module.json"
        if not manifest_path.is_file():
            raise ModuleInstallError("В архиве отсутствует fear-module.json")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModuleInstallError("Некорректный fear-module.json") from exc
        if not isinstance(manifest, dict):
            raise ModuleInstallError("fear-module.json должен содержать JSON-объект")
        if manifest.get("id") != package.module_id or manifest.get("version") != package.version:
            raise ModuleInstallError("ID или версия модуля не совпадают с каталогом FUR")
        if package_root != destination:
            for child in package_root.iterdir():
                shutil.move(str(child), destination / child.name)
            shutil.rmtree(package_root)

    def _install_dependencies(self, module_dir: Path, target: Path) -> None:
        requirements = module_dir / "requirements.lock"
        if not requirements.exists():
            return
        if not requirements.is_file() or requirements.stat().st_size > 100_000:
            raise ModuleInstallError("Некорректный requirements.lock")
        if not any(
            line.strip() and not line.lstrip().startswith("#")
            for line in requirements.read_text(encoding="utf-8").splitlines()
        ):
            return
        try:
            result = subprocess.run(
                [
                    "uv", "pip", "install", "--require-hashes", "--only-binary", ":all:",
                    "--target", str(target), "-r", str(requirements),
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise ModuleInstallError(f"Не удалось запустить установку зависимостей: {exc}") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout)[-1500:]
            raise ModuleInstallError(f"Не удалось установить зависимости: {detail}")

    def install(self, module_id: str, *, update: bool = False) -> str:
        with _MANAGER_OPERATION_LOCK:
            return self._install(module_id, update=update)

    def _install(self, module_id: str, *, update: bool = False) -> str:
        if module_id in _ACTIVE_MODULE_CHANGES:
            raise ModuleInstallError(f"Для {module_id} уже ожидается перезагрузка")
        if not MODULE_ID_RE.fullmatch(module_id) or module_id == "system":
            raise ModuleInstallError("ID модуля содержит недопустимые символы")
        package = self._registry().get(module_id)
        if package is None:
            raise ModuleInstallError(f"Модуль {module_id} не найден в FUR")
        state = self.installed()
        previous_state = state.copy()
        if module_id in state and not update:
            raise ModuleInstallError(f"Модуль {module_id} уже установлен; используйте .fupd")
        if update and module_id not in state:
            raise ModuleInstallError(f"Модуль {module_id} не установлен через FUR")
        if module_id not in state and (self.modules_dir / module_id).exists():
            raise ModuleInstallError(f"Каталог {module_id} уже существует и не управляется FUR")
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self.deps_dir.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{module_id}-", dir=self.modules_dir))
        dep_stage = Path(tempfile.mkdtemp(prefix=f".{module_id}-", dir=self.deps_dir))
        module_target = self.modules_dir / module_id
        dep_target = self.deps_dir / module_id
        backup = self.modules_dir / f".{module_id}-backup"
        dep_backup = self.deps_dir / f".{module_id}-backup"
        had_module, had_deps = module_target.exists(), dep_target.exists()
        try:
            archive_url = FUR_RAW_ROOT + package.archive
            archive_bytes = self._fetch(archive_url, MAX_ARCHIVE_SIZE)
            self._safe_extract(archive_bytes, stage, package)
            self._install_dependencies(stage, dep_stage)
            if backup.exists() or dep_backup.exists():
                raise ModuleInstallError(
                    f"Для {module_id} уже есть незавершённая транзакция"
                )
            if had_module:
                os.replace(module_target, backup)
            if had_deps:
                os.replace(dep_target, dep_backup)
            os.replace(stage, module_target)
            os.replace(dep_stage, dep_target)
            state[module_id] = package.version
            self._write_state(state)
            self._pending[module_id] = (had_module, had_deps, previous_state, True)
            _ACTIVE_MODULE_CHANGES.add(module_id)
            log.info("Installed FUR module %s version %s", module_id, package.version)
            return package.version
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(dep_stage, ignore_errors=True)
            if backup.exists():
                shutil.rmtree(module_target, ignore_errors=True)
                os.replace(backup, module_target)
            elif not had_module:
                shutil.rmtree(module_target, ignore_errors=True)
            if dep_backup.exists():
                shutil.rmtree(dep_target, ignore_errors=True)
                os.replace(dep_backup, dep_target)
            elif not had_deps:
                shutil.rmtree(dep_target, ignore_errors=True)
            if state != previous_state:
                self._write_state(previous_state)
            raise

    def commit(self, module_id: str) -> None:
        with _MANAGER_OPERATION_LOCK:
            if module_id not in self._pending:
                return
            shutil.rmtree(self.modules_dir / f".{module_id}-backup", ignore_errors=True)
            shutil.rmtree(self.deps_dir / f".{module_id}-backup", ignore_errors=True)
            del self._pending[module_id]
            _ACTIVE_MODULE_CHANGES.discard(module_id)

    def rollback(self, module_id: str) -> None:
        with _MANAGER_OPERATION_LOCK:
            pending = self._pending.pop(module_id, None)
            if pending is None:
                return
            had_module, had_deps, previous_state, _installed = pending
            shutil.rmtree(self.modules_dir / module_id, ignore_errors=True)
            shutil.rmtree(self.deps_dir / module_id, ignore_errors=True)
            if had_module:
                os.replace(self.modules_dir / f".{module_id}-backup", self.modules_dir / module_id)
            if had_deps:
                os.replace(self.deps_dir / f".{module_id}-backup", self.deps_dir / module_id)
            self._write_state(previous_state)
            _ACTIVE_MODULE_CHANGES.discard(module_id)
            log.warning("Rolled back FUR module change for %s", module_id)

    def remove(self, module_id: str) -> None:
        with _MANAGER_OPERATION_LOCK:
            self._remove(module_id)

    def _remove(self, module_id: str) -> None:
        if module_id in _ACTIVE_MODULE_CHANGES:
            raise ModuleInstallError(f"Для {module_id} уже ожидается перезагрузка")
        if not MODULE_ID_RE.fullmatch(module_id) or module_id == "system":
            raise ModuleInstallError("ID модуля содержит недопустимые символы")
        state = self.installed()
        if module_id not in state:
            raise ModuleInstallError(f"Модуль {module_id} не установлен через FUR")
        module_target = (self.modules_dir / module_id).resolve()
        dep_target = (self.deps_dir / module_id).resolve()
        if self.modules_dir not in module_target.parents or self.deps_dir not in dep_target.parents:
            raise ModuleInstallError("Путь модуля выходит за пределы каталога установки")
        backup = self.modules_dir / f".{module_id}-backup"
        dep_backup = self.deps_dir / f".{module_id}-backup"
        if backup.exists() or dep_backup.exists():
            raise ModuleInstallError("Для модуля уже выполняется изменение")
        os.replace(module_target, backup)
        try:
            if dep_target.exists():
                os.replace(dep_target, dep_backup)
        except Exception:
            os.replace(backup, module_target)
            raise
        del state[module_id]
        try:
            self._write_state(state)
        except Exception:
            os.replace(backup, module_target)
            if dep_backup.exists():
                os.replace(dep_backup, dep_target)
            raise
        self._pending[module_id] = (True, dep_backup.exists(), state.copy() | {module_id: self.installed_version(backup)}, False)
        _ACTIVE_MODULE_CHANGES.add(module_id)
        log.info("Removed FUR module %s", module_id)

    @staticmethod
    def installed_version(module_dir: Path) -> str:
        try:
            manifest = json.loads((module_dir / "fear-module.json").read_text(encoding="utf-8"))
            return str(manifest["version"])
        except (OSError, KeyError, json.JSONDecodeError):
            return "unknown"
