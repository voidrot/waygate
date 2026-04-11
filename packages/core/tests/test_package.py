from waygate_core import hello


def test_hello_returns_package_greeting() -> None:
    assert hello() == "Hello from waygate-core!"
