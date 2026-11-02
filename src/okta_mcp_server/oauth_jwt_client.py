"""Compatibility layer for tool imports."""

from okta_mcp_server.client import (
    OktaApiTokenClient,
    OktaOAuthJWTClient,
    get_client,
    init_okta_client,
    reset_okta_client,
)

__all__ = [
    "OktaApiTokenClient",
    "OktaOAuthJWTClient",
    "get_client",
    "init_okta_client",
    "reset_okta_client",
]
