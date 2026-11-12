import pytest
from pydantic import ValidationError

from conftest import make_settings


def test_prod_http_requires_auth():
    with pytest.raises(ValidationError, match="Refusing"):
        make_settings(env="prod", transport="http", auth="none")


def test_static_needs_long_token():
    with pytest.raises(ValidationError):
        make_settings(auth="static", dev_token="short")


def test_jwt_needs_a_key_source():
    with pytest.raises(ValidationError):
        make_settings(auth="jwt")


def test_port_env_wins(monkeypatch):
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("MCP_PORT", "8000")
    assert make_settings().port == 9090


def test_comma_lists(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "a.example.com, b.example.com")
    assert make_settings().allowed_hosts == ["a.example.com", "b.example.com"]
