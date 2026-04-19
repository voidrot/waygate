from waygate_core.config.registry import ConfigRegistry


class _NoPluginManager:
    def get_plugin_configs(self):
        return {}


def test_llm_workflow_profiles_env_json(monkeypatch) -> None:
    monkeypatch.setenv(
        "WAYGATE_CORE__LLM_WORKFLOW_PROFILES",
        '{"draft":{"model_name":"qwen3.5:9b","common_options":{"temperature":0.2},"provider_options":{"OllamaProvider":{"num_ctx":4096}}}}',
    )

    settings = ConfigRegistry(_NoPluginManager()).build_config()

    draft = settings.core.llm_workflow_profiles["draft"]
    assert draft.model_name == "qwen3.5:9b"
    assert draft.common_options.temperature == 0.2
    assert draft.provider_options["OllamaProvider"]["num_ctx"] == 4096
