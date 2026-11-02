from typing import Optional

from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.context import get_caller_email
from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.oauth_jwt_client import get_client


@mcp.tool()
def get_logs(
    limit: int = 100,
    ctx: Context | None = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    filter: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """Retrieve system logs from Okta (requires logs.read scope)."""
    caller = get_caller_email()

    logger.info(f"[caller={caller}] Retrieving system logs limit={limit}, since={since}, until={until}")

    params = {"limit": limit}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if filter:
        params["filter"] = filter
    if query:
        params["q"] = query

    try:
        logs = get_client().get("/api/v1/logs", params=params)
        logger.info(f"[caller={caller}] Retrieved {len(logs)} log entries")
        return {"logs": logs, "count": len(logs), "since": since, "until": until}
    except PermissionError as e:
        logger.error(f"[caller={caller}] Permission denied: {e!s}")
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error retrieving logs: {e!s}")
        raise
