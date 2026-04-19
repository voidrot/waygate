"""Core configuration models used by the WayGate settings registry."""

import json

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    RedisDsn,
    TypeAdapter,
    field_validator,
)
from typing import cast

from waygate_core.plugin.llm import LLMCommonOptions, LLMOptionPolicy


DEFAULT_REDIS_DSN: RedisDsn = TypeAdapter(RedisDsn).validate_python(
    "redis://localhost:6379/0"
)


class LLMWorkflowProfile(BaseModel):
    """Per-workflow model and option defaults for LLM invocations."""

    model_name: str | None = Field(default=None)
    common_options: LLMCommonOptions = Field(default_factory=LLMCommonOptions)
    provider_options: dict[str, dict[str, object]] = Field(default_factory=dict)
    option_policy: LLMOptionPolicy = Field(default=LLMOptionPolicy.STRICT)


class CoreSettings(BaseModel):
    """Core configuration settings for WayGate."""

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
    template_packages: list[str] = Field(default_factory=lambda: ["waygate_core"])
    raw_doc_template: str = Field(
        default="raw_document.j2",
        validation_alias=AliasChoices("raw_doc_template", "raw_document_template"),
    )
    draft_doc_template: str = Field(
        default="draft_source_text.j2",
        validation_alias=AliasChoices(
            "draft_doc_template",
            "draft_document_template",
        ),
    )
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
    llm_workflow_profiles: dict[str, LLMWorkflowProfile] = Field(default_factory=dict)

    @field_validator("template_packages", mode="before")
    @classmethod
    def _parse_template_packages(cls, value: object) -> list[str]:
        """Normalize template package values into a list.

        Args:
            value: The raw template package setting value.

        Returns:
            A non-empty list of package names.
        """

        if value is None:
            return ["waygate_core"]
        if isinstance(value, str):
            parsed = [item.strip() for item in value.split(",") if item.strip()]
            return parsed or ["waygate_core"]
        if isinstance(value, list):
            parsed = [str(item).strip() for item in value if str(item).strip()]
            return parsed or ["waygate_core"]
        return ["waygate_core"]

    @field_validator("llm_workflow_profiles", mode="before")
    @classmethod
    def _parse_llm_workflow_profiles(
        cls,
        value: object,
    ) -> dict[str, LLMWorkflowProfile]:
        """Parse workflow profile overrides from JSON or a mapping.

        Args:
            value: The raw workflow profile setting value.

        Returns:
            A mapping of workflow names to profile objects.

        Raises:
            ValueError: If the value cannot be interpreted as a mapping or JSON
                object.
        """

        if value is None:
            return {}
        if isinstance(value, str):
            if not value.strip():
                return {}
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError("llm_workflow_profiles must be a JSON object")
            return cast(dict[str, LLMWorkflowProfile], parsed)
        if isinstance(value, dict):
            return cast(dict[str, LLMWorkflowProfile], value)
        raise ValueError("llm_workflow_profiles must be a mapping or JSON string")
