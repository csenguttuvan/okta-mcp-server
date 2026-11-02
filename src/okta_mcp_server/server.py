"""Main entry point for Okta MCP Server."""

import os
import sys
from pathlib import Path

from loguru import logger

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=os.getenv("OKTA_LOG_LEVEL", "INFO"),
)

from okta_mcp_server.client import init_okta_client
from okta_mcp_server.context import (
    caller_email_var,
    caller_groups_var,
)
from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.tool_loader import load_tools


def initialize():
    """Initialize client and register tools."""
    logger.info("Step 1: Initializing Okta client...")
    init_okta_client()
    logger.info("✅ Okta client initialized successfully")

    logger.info("Step 2: Registering MCP tools...")
    okta_scopes = os.getenv("OKTA_SCOPES", "")
    registered_tools = load_tools(okta_scopes)
    logger.info(f"✅ {len(registered_tools)} MCP tools registered")
    return registered_tools


def main():
    """Run the Okta MCP server."""
    registered_tools = initialize()

    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport in ("http", "sse"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))

        logger.info(f"Running in HTTP/SSE transport mode on {host}:{port}")

        import uvicorn
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Mount, Route

        async def health_check(request):
            """Healthcheck endpoint."""
            if request.method == "HEAD":
                return Response(status_code=200)
            return JSONResponse({"status": "healthy", "tools_count": len(registered_tools)})

        class CallerContextMiddleware:
            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    headers = {
                        key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])
                    }
                    email = headers.get("x-user-email") or headers.get("x-forwarded-user") or "unknown"
                    groups_str = headers.get("x-user-groups", "")
                    groups = [g.strip() for g in groups_str.split(",") if g.strip()]

                    token_email = caller_email_var.set(email)
                    token_groups = caller_groups_var.set(groups)
                    try:
                        await self.app(scope, receive, send)
                    finally:
                        caller_email_var.reset(token_email)
                        caller_groups_var.reset(token_groups)
                else:
                    await self.app(scope, receive, send)

        mcp_sse_app = mcp.sse_app()
        starlette_app = Starlette(
            routes=[
                Route("/health", health_check, methods=["GET", "HEAD"]),
                Mount("/", app=mcp_sse_app),
            ]
        )
        app = CallerContextMiddleware(starlette_app)
        uvicorn.run(app, host=host, port=port)
    else:
        logger.info("Running in stdio transport mode (standard for Claude Desktop / Cursor / Claude Code)")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
