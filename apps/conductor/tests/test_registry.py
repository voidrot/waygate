import importlib
import sys


def test_conductor_registry_resolves_local_storage_plugin() -> None:
    sys.modules.pop("waygate_conductor.registry", None)

    registry_module = importlib.import_module("waygate_conductor.registry")

    assert registry_module.core_config.storage_plugin_name == "local-storage"
    assert registry_module.storage.name == "local-storage"
