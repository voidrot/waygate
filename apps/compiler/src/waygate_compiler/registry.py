from waygate_core.config.schema import CoreSettings
from waygate_core.config import ConfigRegistry

config_registry = ConfigRegistry()
config_registry.discover()

_core_config: CoreSettings | None = config_registry.get("core")
core_config = _core_config if _core_config is not None else CoreSettings()
