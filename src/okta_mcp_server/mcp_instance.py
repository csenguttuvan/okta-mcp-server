"""Shared MCP instance for all tools to import."""

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP("Okta MCP Server", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
