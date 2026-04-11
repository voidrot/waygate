from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerConfig(BaseSettings):
    """
    Configuration settings for the Waygate Scheduler application.
    """

    pg_user: str = Field(default="postgres")
    pg_password: str = Field(default="postgres")
    pg_host: str = Field(default="localhost")
    pg_port: int = Field(default=5432)
    pg_db: str = Field(default="postgres")

    model_config = SettingsConfigDict(env_prefix="waygate_scheduler_")
