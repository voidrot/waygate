from pydantic import RedisDsn, Field, AliasChoices, TypeAdapter, BaseModel


DEFAULT_REDIS_DSN: RedisDsn = TypeAdapter(RedisDsn).validate_python(
    "redis://localhost:6379/0"
)


class CoreSettings(BaseModel):
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

    storage_plugin_name: str = Field(default="local-storage")
    llm_plugin_name: str = Field(default="OllamaProvider")
    communication_plugin_name: str = Field(default="communication-http")
    metadata_model_name: str = Field(
        default="qwen3.5:9b",
        validation_alias=AliasChoices("metadata_model_name", "metadata_model"),
    )
    draft_model_name: str = Field(
        default="qwen3.5:9b",
        validation_alias=AliasChoices("draft_model_name", "draft_model"),
    )
    review_model_name: str = Field(
        default="hermes3:8b",
        validation_alias=AliasChoices("review_model_name", "review_model"),
    )
