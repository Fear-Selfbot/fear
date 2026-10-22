import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fear_module import FearModule

if TYPE_CHECKING:
    from src.core.client import FearClient

log = logging.getLogger(__name__)


class ModuleLoader:
    def __init__(self, modules_path: Path, dependency_path: Path | None = None):
        self.modules_path = modules_path
        self.dependency_path = dependency_path or modules_path.parent / ".data" / "module-deps"
        self.modules: list[FearModule] = []

    def load(self, client: FearClient) -> list[FearModule]:
        self.modules.clear()

        legacy_path = Path(__file__).resolve().parents[2] / "modules"

        dependency_root = self.dependency_path
        if dependency_root.is_dir():
            for dependency_path in sorted(dependency_root.glob("*"), reverse=True):
                if (
                    dependency_path.is_dir()
                    and not dependency_path.name.startswith(".")
                    and str(dependency_path) not in sys.path
                ):
                    sys.path.insert(0, str(dependency_path))
        importlib.invalidate_caches()

        candidates = [
            *((path, "modules") for path in self.modules_path.glob("*/main.py")),
            *(
                (path, "src.modules")
                for path in legacy_path.glob("*/main.py")
                if legacy_path != self.modules_path
            ),
        ]
        for main_file, package_root in sorted(candidates, key=lambda item: str(item[0])):
            module_name = main_file.parent.name
            if module_name.startswith("."):
                continue
            import_path = f"{package_root}.{module_name}.main"
            log.debug("Importing Fear module entrypoint %s", main_file)
            try:
                for loaded_name in tuple(sys.modules):
                    if loaded_name == f"{package_root}.{module_name}" or loaded_name.startswith(
                        f"{package_root}.{module_name}."
                    ):
                        del sys.modules[loaded_name]
                importlib.invalidate_caches()
                imported = importlib.import_module(import_path)

                for _, cls in inspect.getmembers(imported, inspect.isclass):
                    if (
                        issubclass(cls, FearModule)
                        and cls is not FearModule
                        and cls.__module__ == imported.__name__
                    ):
                        module = cls(client)
                        module.register()
                        self.modules.append(module)
                        log.info(
                            "Registered Fear module %s v%s", module.name, module.version
                        )
            except Exception:
                log.exception("Failed to load Fear module %s", module_name)
                raise

        if not self.modules:
            log.info("No Fear modules were found in %s", self.modules_path)

        return self.modules
