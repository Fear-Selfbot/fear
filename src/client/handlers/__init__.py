import importlib
import pkgutil

from dispyro import Router


def get_routers() -> list[Router]:
    routers = []

    # Find all modules in handlers
    for module_info in pkgutil.walk_packages(
        __path__,
        prefix=f"{__name__}.",
    ):
        module = importlib.import_module(module_info.name)

        router = getattr(module, "router", None)

        if isinstance(router, Router):
            routers.append(router)

    return routers
