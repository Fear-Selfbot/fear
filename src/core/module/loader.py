import importlib
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fear_module import FearModule

if TYPE_CHECKING:
    from src.core.client import FearClient


class ModuleLoader:
    def __init__(self, modules_path: Path):
        self.modules_path = modules_path
        self.modules: list[FearModule] = []

    def load(self, client: FearClient) -> list[FearModule]:
        self.modules.clear()

        for main_file in sorted(self.modules_path.glob("*/main.py")):
            module_name = main_file.parent.name
            import_path = f"src.modules.{module_name}.main"

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

        return self.modules
