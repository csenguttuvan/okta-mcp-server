from typing import Any, Dict, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.context import get_caller_email
from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.oauth_jwt_client import get_client


@mcp.tool()
def list_applications(
    ctx: Context | None = None,
    limit: int = 20,
    after: Optional[str] = None,
    filter: Optional[str] = None,
    search: Optional[str] = None,  # ← ADD THIS
) -> str:
    """List all applications in the Okta organization.

    Args:
        limit: Maximum number of applications to return (default 20)
        after: Pagination cursor for next page
        filter: Filter expression (e.g., 'status eq "ACTIVE"')
        search: Search term to filter by app name (case-insensitive substring match)

    Returns:
        String containing formatted list of applications
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Listing applications limit={limit} search={search}")

    params = {"limit": limit}
    if after:
        params["after"] = after
    if filter:
        params["filter"] = filter
    if search:
        # Okta supports q= for app name search
        params["q"] = search

    try:
        client = get_client()
        apps = client.get("/api/v1/apps", params=params)
        logger.info(f"[caller={caller}] Found {len(apps)} applications")

        if not apps:
            return f"No applications found{f' matching {search!r}' if search else ''}."

        lines = [f"Found {len(apps)} applications:\n"]
        for app in apps:
            lines.append(
                f"• {app.get('label', 'N/A')} (ID: {app.get('id', 'N/A')})\n"
                f"  Status: {app.get('status', 'N/A')}, Sign-on: {app.get('signOnMode', 'N/A')}"
            )
        return "\n".join(lines)

    except PermissionError as e:
        return f"❌ Permission denied: {e!s}"
    except Exception as e:
        return f"❌ Error listing applications: {e!s}"


@mcp.tool()
def get_application(ctx: Context | None = None, app_id: str = "") -> Optional[Dict[str, Any]]:
    """Get details of a specific application by ID.

    Args:
        app_id: The Okta application ID

    Returns:
        Dict containing application details
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Getting application: {app_id}")

    if not app_id:
        logger.error(f"[caller={caller}] app_id is required")
        raise ValueError("app_id is required")

    try:
        client = get_client()
        app = client.get(f"/api/v1/apps/{app_id}")
        logger.info(f"[caller={caller}] Retrieved application: {app.get('label', 'N/A')}")
        return app
    except PermissionError as e:
        logger.error(f"[caller={caller}] Permission denied: {e!s}")
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error getting application: {e!s}")
        raise


@mcp.tool()
def find_application(
    ctx: Context | None = None,
    names: list[str] = [],
) -> str:
    """Fuzzy search for Okta applications by name. Use when exact app name is unknown.
    Alias for find_application with a single query string.

    Args:
        query: Partial or full application name to search for (case-insensitive)

    Returns:
        String containing matched applications with their IDs

    Example: { "query": "databricks" }
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Finding applications: {names}")

    if not names:
        return "❌ Please provide at least one application name to search for."

    client = get_client()
    results = {}

    for name in names:
        try:
            # Use Okta's q= param for server-side name search
            apps = client.get("/api/v1/apps", params={"q": name, "limit": 10})

            if not apps:
                results[name] = "❌ Not found"
                continue

            # Exact match first, then fuzzy
            name_lower = name.lower()
            exact = [a for a in apps if a.get("label", "").lower() == name_lower]
            matches = exact if exact else apps

            results[name] = [
                {
                    "id": a.get("id"),
                    "label": a.get("label"),
                    "status": a.get("status"),
                    "signOnMode": a.get("signOnMode"),
                }
                for a in matches[:3]  # Return top 3 matches max
            ]

        except Exception as e:
            results[name] = f"❌ Error: {e!s}"

    # Format output
    lines = []
    for name, matches in results.items():
        lines.append(f"\n🔍 Search: '{name}'")
        if isinstance(matches, str):
            lines.append(f"  {matches}")
        else:
            for m in matches:
                lines.append(
                    f"  • {m['label']} (ID: {m['id']})\n    Status: {m['status']}, Sign-on: {m['signOnMode']}"
                )
    return "\n".join(lines)


@mcp.tool()
def search_applications_fuzzy(
    query: str,
    ctx: Context | None = None,
    limit: int = 50,
) -> str:
    """Fuzzy search for Okta applications by name. Use when exact app name is unknown.

    Args:
        query: Partial or full application name to search for (case-insensitive)
        limit: Maximum number of applications to scan (default 50)

    Returns:
        String containing matched applications with their IDs
    Example: { "query": "databricks" }
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Fuzzy searching applications: query={query!r}")

    if not query:
        return "❌ Please provide a search query."

    try:
        client = get_client()
        # Use Okta's q= for server-side pre-filter, then fuzzy match client-side
        apps = client.get("/api/v1/apps", params={"q": query, "limit": limit})

        if not apps:
            return f"No applications found matching '{query}'."

        query_lower = query.lower()
        matches = [
            app
            for app in apps
            if query_lower in app.get("label", "").lower() or query_lower in app.get("name", "").lower()
        ]

        if not matches:
            return f"No applications found matching '{query}'."

        logger.info(f"[caller={caller}] Found {len(matches)} apps matching '{query}'")

        lines = [f"Found {len(matches)} application(s) matching '{query}':\n"]
        for app in matches:
            lines.append(
                f"• {app.get('label', 'N/A')} (ID: {app.get('id', 'N/A')})\n"
                f"  Status: {app.get('status', 'N/A')}, Sign-on: {app.get('signOnMode', 'N/A')}"
            )
        return "\n".join(lines)

    except PermissionError as e:
        logger.error(f"[caller={caller}] Permission denied: {e!s}")
        return f"❌ Permission denied: {e!s}"
    except Exception as e:
        logger.error(f"[caller={caller}] Error searching applications: {e!s}")
        return f"❌ Error searching applications: {e!s}"


@mcp.tool()
def list_application_users(ctx: Context | None = None, app_id: str = "", limit: int = 50) -> Dict[str, Any]:
    """List users assigned to an application.

    Args:
        app_id: The Okta application ID
        limit: Maximum number of users to return

    Returns:
        Dict containing list of assigned users
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Listing users for application: {app_id}")

    if not app_id:
        logger.error(f"[caller={caller}] app_id is required")
        raise ValueError("app_id is required")

    params = {"limit": limit}

    try:
        client = get_client()
        users = client.get(f"/api/v1/apps/{app_id}/users", params=params)
        logger.info(f"[caller={caller}] Found {len(users)} users for application {app_id}")
        return {"users": users, "count": len(users), "app_id": app_id}
    except PermissionError as e:
        logger.error(f"[caller={caller}] Permission denied: {e!s}")
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error listing application users: {e!s}")
        raise


@mcp.tool()
def list_application_groups(ctx: Context | None = None, app_id: str = "", limit: int = 50) -> Dict[str, Any]:
    """List groups assigned to an application.

    Args:
        app_id: The Okta application ID
        limit: Maximum number of groups to return

    Returns:
        Dict containing list of assigned groups
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Listing groups for application: {app_id}")

    if not app_id:
        logger.error(f"[caller={caller}] app_id is required")
        raise ValueError("app_id is required")

    params = {"limit": limit}

    try:
        client = get_client()
        groups = client.get(f"/api/v1/apps/{app_id}/groups", params=params)
        logger.info(f"[caller={caller}] Found {len(groups)} groups for application {app_id}")
        return {"groups": groups, "count": len(groups), "app_id": app_id}
    except PermissionError as e:
        logger.error(f"[caller={caller}] Permission denied: {e!s}")
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error listing application groups: {e!s}")
        raise


@mcp.tool()
@mcp.tool()
def search_aws_applications_by_account(ctx: Context | None = None, account_id: str = "") -> Dict[str, Any]:
    """Search AWS applications by AWS account ID."""
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Searching AWS applications for account ID: {account_id}")

    if not account_id:
        logger.error(f"[caller={caller}] account_id is required")
        raise ValueError("account_id is required")

    try:
        client = get_client()

        apps = client.get("/api/v1/apps", params={"limit": 200})
        matches = []

        for app in apps:
            app_name = app.get("label", "")
            app_id = app.get("id")
            sign_on_mode = app.get("signOnMode")

            if sign_on_mode != "SAML_2_0":
                continue

            if "AWS" not in app_name and "amazon" not in app_name.lower():
                continue

            try:
                app_details = client.get(f"/api/v1/apps/{app_id}")
                settings = app_details.get("settings", {})
                app_settings = settings.get("app", {})
                sign_on_settings = settings.get("signOn", {})

                identity_provider_arn = app_settings.get("identityProviderArn", "")
                parsed_account_id = None

                if "arn:aws:iam::" in identity_provider_arn:
                    parts = identity_provider_arn.split(":")
                    if len(parts) >= 5:
                        parsed_account_id = parts[4]

                searchable_blob = " ".join(
                    [
                        str(app_name),
                        str(app_settings),
                        str(sign_on_settings),
                    ]
                )

                if account_id == parsed_account_id or account_id in searchable_blob:
                    match_info = {
                        "name": app_name,
                        "id": app_id,
                        "status": app_details.get("status"),
                        "signOnMode": sign_on_mode,
                        "aws_account_id": parsed_account_id,
                        "identityProviderArn": identity_provider_arn,
                        "app_settings": app_settings,
                    }
                    matches.append(match_info)
                    logger.info(f"[caller={caller}] ✅ Found match: {app_name} ({app_id})")

            except Exception as e:
                logger.warning(f"[caller={caller}] Could not check app {app_id}: {e!s}")
                continue

        logger.info(f"[caller={caller}] Found {len(matches)} application(s) with account ID {account_id}")

        return {
            "success": True,
            "account_id": account_id,
            "matches": matches,
            "total_matches": len(matches),
            "message": (
                f"Found {len(matches)} AWS application(s) containing account ID {account_id}"
                if matches
                else f"No AWS applications found containing account ID {account_id}"
            ),
        }

    except PermissionError as e:
        logger.error(f"[caller={caller}] ❌ Permission denied: {e!s}")
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] ❌ Error searching AWS applications: {e!s}")
        raise
