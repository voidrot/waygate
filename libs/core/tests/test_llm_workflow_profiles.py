from waygate_core.plugin.llm import LLMOptionPolicy
from waygate_core.config.registry import ConfigRegistry


class _NoPluginManager:
    def get_plugin_configs(self):
        return {}


def test_llm_workflow_profiles_env_json(monkeypatch) -> None:
    monkeypatch.setenv(
        "WAYGATE_CORE__LLM_WORKFLOW_PROFILES",
        '{"draft":{"model_name":"qwen3.5:9b","common_options":{"temperature":0.2},"provider_options":{"OllamaProvider":{"num_ctx":4096}},"option_policy":"permissive"}}',
    )

    settings = ConfigRegistry(_NoPluginManager()).build_config()

    draft = settings.core.llm_workflow_profiles["draft"]
    assert draft.model_name == "qwen3.5:9b"
    assert draft.common_options.temperature == 0.2
    assert draft.provider_options["OllamaProvider"]["num_ctx"] == 4096
    assert draft.option_policy is LLMOptionPolicy.PERMISSIVE


def test_template_packages_env_plain_string(monkeypatch) -> None:
    monkeypatch.setenv("WAYGATE_CORE__TEMPLATE_PACKAGES", "waygate_core")

    settings = ConfigRegistry(_NoPluginManager()).build_config()

    assert settings.core.template_packages == ["waygate_core"]
