from waygate_core.doc_helpers import slugify


def test_pytest_bootstrap_imports_workspace_packages() -> None:
    assert slugify("WayGate Testing Setup") == "waygate-testing-setup"
