from src.main import app


def test_package_imports() -> None:
    assert app is not None
