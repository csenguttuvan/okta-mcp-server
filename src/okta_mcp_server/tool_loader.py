"""Tool registration for the standalone Okta MCP server.

Importing a tool module is what registers its ``@mcp.tool()`` functions.
By default, all tools (read + admin) are loaded.
If ``OKTA_READ_ONLY=true`` is set or ``OKTA_SCOPES`` does not contain any
manage scopes, only read-only tools are registered.
"""

import os
import sys

from loguru import logger

from okta_mcp_server.mcp_instance import mcp

MANAGE_SCOPES = ("okta.users.manage", "okta.groups.manage", "okta.apps.manage")


def is_read_only_mode(scopes: str = "") -> bool:
    """Determine whether the server should run in read-only mode."""
    read_only_env = os.getenv("OKTA_READ_ONLY", "").strip().lower()
    if read_only_env in ("true", "1", "yes"):
        return True

    # If OAuth scopes are provided, obey scope boundaries
    if scopes and not any(scope in scopes for scope in MANAGE_SCOPES):
        return True

    return False


def registered_tool_names() -> list[str]:
    """Return all currently registered MCP tool names."""
    return sorted(tool.name for tool in mcp._tool_manager.list_tools())


def load_tools(scopes: str = "") -> list[str]:
    """Import tool modules based on configured mode and return registered tool names."""
    # Always import base inspection/read tools
    from okta_mcp_server.tools.applications import applications
    from okta_mcp_server.tools.groups import groups
    from okta_mcp_server.tools.policies import policies
    from okta_mcp_server.tools.system_logs import system_logs
    from okta_mcp_server.tools.users import users

    read_only = is_read_only_mode(scopes)

    if not read_only:
        logger.info("Admin mode active: importing management and write tools...")
        from okta_mcp_server.tools.applications import applications_admin
        from okta_mcp_server.tools.groups import groups_admin
        from okta_mcp_server.tools.policies import policies_admin
        from okta_mcp_server.tools.rules import group_rules
        from okta_mcp_server.tools.users import users_admin
    else:
        logger.info("Read-only mode active: administrative modification tools disabled")

    tools = registered_tool_names()
    logger.info(f"Successfully registered {len(tools)} Okta MCP tools")
    return tools


if __name__ == "__main__":
    scopes = os.getenv("OKTA_SCOPES", "")
    tools = load_tools(scopes)
    print(f"Registered {len(tools)} tools:")
    for t in tools:
        print(f"  - {t}")
    sys.exit(0)
