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
    def __init__(self, modules_path: Path):
        self.modules_path = modules_path
        self.modules: list[FearModule] = []

    def load(self, client: FearClient) -> list[FearModule]:
        self.modules.clear()

        for main_file in sorted(self.modules_path.glob("*/main.py")):
            module_name = main_file.parent.name
            import_path = f"src.modules.{module_name}.main"
            log.debug("Importing Fear module entrypoint %s", main_file)
            try:
                if import_path in sys.modules:
                    imported = importlib.reload(sys.modules[import_path])
                else:
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
                        log.info("Registered Fear module %s v%s", module.name, module.version)
            except Exception:
                log.exception("Failed to load Fear module %s", module_name)
                raise

        if not self.modules:
            log.info("No Fear modules were found in %s", self.modules_path)

        return self.modules
