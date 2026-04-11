from pydantic import RedisDsn, Field, AliasChoices, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_REDIS_DSN: RedisDsn = TypeAdapter(RedisDsn).validate_python(
    "redis://localhost:6379/0"
)


class CoreSettings(BaseSettings):
    """
    Core configuration settings for Waygate.
    """

    pg_user: str = Field(default="postgres")
    pg_password: str = Field(default="postgres")
    pg_host: str = Field(default="localhost")
    pg_port: int = Field(default=5432)
    pg_db: str = Field(default="postgres")

    redis_dsn: RedisDsn = Field(
        DEFAULT_REDIS_DSN, validation_alias=AliasChoices("redis_url")
    )

    draft_queue_name: str = Field(default="draft_queue")

    model_config = SettingsConfigDict(env_prefix="waygate_")
