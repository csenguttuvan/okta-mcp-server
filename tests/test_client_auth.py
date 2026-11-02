import pytest

from okta_mcp_server.client import (
    OktaApiTokenClient,
    init_okta_client,
    reset_okta_client,
)


def test_api_token_client_headers():
    client = OktaApiTokenClient(
        base_url="https://example.okta.com",
        api_token="test_token_12345",
    )
    headers = client.get_headers()
    assert headers["Authorization"] == "SSWS test_token_12345"
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"


def test_api_token_initialization(monkeypatch):
    reset_okta_client()
    monkeypatch.setenv("OKTA_API_BASE_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "ssws_secret_token")
    monkeypatch.delenv("OKTA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OKTA_PRIVATE_KEY_PATH", raising=False)

    client = init_okta_client()
    assert isinstance(client, OktaApiTokenClient)
    assert client.base_url == "https://example.okta.com"
    assert client.get_headers()["Authorization"] == "SSWS ssws_secret_token"


def test_missing_credentials_raises_helpful_error(monkeypatch):
    reset_okta_client()
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    monkeypatch.delenv("OKTA_CLIENT_ID", raising=False)
    monkeypatch.delenv("OKTA_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("OKTA_API_BASE_URL", "https://example.okta.com")

    with pytest.raises(ValueError) as excinfo:
        init_okta_client()

    err_msg = str(excinfo.value)
    assert "OKTA_API_TOKEN" in err_msg
    assert "OKTA_CLIENT_ID" in err_msg
