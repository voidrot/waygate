from pathlib import Path


def test_provider_readme_documents_base_url_env_var() -> None:
    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text()

    assert "WAYGATE_OLLAMAPROVIDER__BASE_URL" in content
    assert "WAYGATE_OLLAMAPROVIDER__VALIDATE_MODEL_ON_INIT" in content
