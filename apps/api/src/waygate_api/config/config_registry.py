from waygate_core.config import ConfigRegistry

config_registry = ConfigRegistry()
config_registry.discover()


core_config = config_registry.get("core")
