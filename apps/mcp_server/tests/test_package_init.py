import importlib
import sys


def test_package_import_does_not_eagerly_import_server() -> None:
    for module_name in ["mcp_server", "mcp_server.server", "mcp_server.config"]:
        sys.modules.pop(module_name, None)

    package = importlib.import_module("mcp_server")

    assert package.main is not None
    assert "mcp_server.server" not in sys.modules
    assert "mcp_server.config" not in sys.modules
