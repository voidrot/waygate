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

    celery_broker_dsn: str = Field(
        default="pyamqp://user:password@localhost:5672//",
        description="The DSN for connecting to RabbitMQ, used for task queuing.",
    )
    celery_result_backend_dsn: str = Field(
        default="db+postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        description="The DSN for connecting to PostgreSQL, used for storing Celery task results.",
    )

    storage_plugin_name: str = Field(default="local-storage")
