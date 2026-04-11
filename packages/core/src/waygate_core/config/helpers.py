from pydantic.alias_generators import to_snake, to_pascal
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import create_model
from typing import Tuple, Any


class ConfigBuilder:
    def __init__(self, name: str, prefix: str | None = None):
        self._name = name
        self._settings = {}
        self._env_prefix = self._build_env_prefix(prefix)

    def _build_env_prefix(self, prefix: str | None) -> str:
        if prefix is None:
            return f"waygate_{to_snake(self._name)}_".upper()
        snake = to_snake(prefix).upper()
        return f"{snake}_"

    def _build_model_name(self) -> str:
        return f"{to_pascal(to_snake(self._name))}Config"

    def add_config(self, name: str, type_default: Tuple[type, Any]):
        """
        Add a configuration setting.

        Args:
            name: The name of the configuration setting.
            type_default: A tuple containing the type and default value of the setting.
        """
        self._settings[name] = type_default

    def build(self) -> None:
        """
        Build the configuration schema.

        Returns:
            A Pydantic model class representing the configuration schema.
        """
        from pydantic import Field

        fields: dict[str, Any] = {
            name: (type_default[0], Field(default=type_default[1]))
            for name, type_default in self._settings.items()
        }

        model_name: str = self._build_model_name()

        self._model = create_model(
            model_name,
            __base__=BaseSettings,
            __config__=SettingsConfigDict(env_prefix=self._env_prefix),
            **fields,
        )

    def get_model(self) -> type[BaseSettings]:
        """
        Get the built configuration model.

        Returns:
            The Pydantic model class representing the configuration schema.
        """
        return self._model
