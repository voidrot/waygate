from pathlib import Path


def test_provider_readme_documents_required_env_vars() -> None:
    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text()

    assert "WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY" in content
    assert "WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_BASE_URL" in content
