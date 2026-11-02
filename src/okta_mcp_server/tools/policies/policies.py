from typing import Any, Dict, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.oauth_jwt_client import get_client


def get_caller_email(ctx: Context | None) -> str:
    """Extract user email from context metadata"""
    if not ctx:
        return "unknown"

    # Try to get from request context meta (when using gateway)
    if hasattr(ctx, "request_context") and hasattr(ctx.request_context, "meta"):
        meta = ctx.request_context.meta
        if isinstance(meta, dict):
            return meta.get("user_email", "unknown")

    # Fallback to environment variable (for non-gateway usage)
    import os

    return os.getenv("USER_EMAIL", "unknown")


@mcp.tool()
def list_policies(
    ctx: Context | None = None,
    type: str = "",
    limit: Optional[int] = 20,
    status: Optional[str] = None,
    q: Optional[str] = None,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """List all the policies from the Okta organization.

    Parameters:
        type (str, required): Specifies the type of policy to return. Available policy types
            are: OKTA_SIGN_ON, PASSWORD, MFA_ENROLL, IDP_DISCOVERY, ACCESS_POLICY,
            PROFILE_ENROLLMENT, POST_AUTH_SESSION, ENTITY_RISK
        status (str, optional): Refines the query by the status of the policy - ACTIVE or INACTIVE.
        q (str, optional): A query string to search policies by name.
        limit (int, optional): Number of results to return (min 20, max 100).
        after (str, optional): Specifies the pagination cursor for the next page of policies.

    Returns:
        Dict containing:
            - policies (List[Dict]): List of policy dictionaries, each containing policy details
            - error (str): Error message if the operation fails
    """
    caller = get_caller_email(ctx)
    logger.info(f"[caller={caller}] Listing policies from Okta organization")
    logger.debug(f"[caller={caller}] Type: {type}, Status: {status}, Q: {q}, limit: {limit}")

    # Validate limit parameter range
    if limit is not None:
        if limit < 20:
            logger.warning(f"[caller={caller}] Limit {limit} is below minimum 20, setting to 20")
            limit = 20
        elif limit > 100:
            logger.warning(f"[caller={caller}] Limit {limit} exceeds maximum 100, setting to 100")
            limit = 100

    if not type:
        logger.error(f"[caller={caller}] type parameter is required")
        return {"error": "type parameter is required"}

    try:
        client = get_client()
        params = {"type": type, "limit": limit}
        if status:
            params["status"] = status
        if q:
            params["q"] = q
        if after:
            params["after"] = after

        logger.debug(f"[caller={caller}] Calling Okta API to list policies")
        policies = client.get("/api/v1/policies", params=params)

        if not policies:
            logger.info(f"[caller={caller}] No policies found")
            return {"policies": []}

        logger.info(f"[caller={caller}] Successfully retrieved {len(policies)} policies")
        return {"policies": policies}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception listing policies: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_policy(ctx: Context | None = None, policy_id: str = "") -> Optional[Dict[str, Any]]:
    """Retrieve a specific policy by ID.

    Parameters:
        policy_id (str, required): The ID of the policy to retrieve.

    Returns:
        Dict containing the policy details.
    """
    caller = get_caller_email(ctx)
    logger.info(f"[caller={caller}] Getting policy: {policy_id}")

    if not policy_id:
        logger.error(f"[caller={caller}] policy_id is required")
        return {"error": "policy_id is required"}

    try:
        client = get_client()
        policy = client.get(f"/api/v1/policies/{policy_id}")
        logger.info(f"[caller={caller}] Successfully retrieved policy {policy_id}")
        return policy
    except Exception as e:
        logger.error(f"[caller={caller}] Exception getting policy: {e}")
        return {"error": str(e)}


@mcp.tool()
def list_policy_rules(ctx: Context | None = None, policy_id: str = "") -> Dict[str, Any]:
    """List all rules for a specific policy.

    Parameters:
        policy_id (str, required): The ID of the policy.

    Returns:
        Dict containing:
            - rules (List[Dict]): List of policy rule dictionaries
            - error (str): Error message if the operation fails
    """
    caller = get_caller_email(ctx)
    logger.info(f"[caller={caller}] Listing rules for policy: {policy_id}")

    if not policy_id:
        logger.error(f"[caller={caller}] policy_id is required")
        return {"error": "policy_id is required"}

    try:
        client = get_client()
        rules = client.get(f"/api/v1/policies/{policy_id}/rules")

        if not rules:
            logger.info(f"[caller={caller}] No policy rules found")
            return {"rules": []}

        logger.info(f"[caller={caller}] Successfully retrieved {len(rules)} rules")
        return {"rules": rules}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception listing policy rules: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_policy_rule(ctx: Context | None = None, policy_id: str = "", rule_id: str = "") -> Optional[Dict[str, Any]]:
    """Retrieve a specific policy rule.

    Parameters:
        policy_id (str, required): The ID of the policy.
        rule_id (str, required): The ID of the rule.

    Returns:
        Dict containing the policy rule details.
    """
    caller = get_caller_email(ctx)
    logger.info(f"[caller={caller}] Getting policy rule: {rule_id} from policy: {policy_id}")

    if not policy_id or not rule_id:
        logger.error(f"[caller={caller}] policy_id and rule_id are required")
        return {"error": "policy_id and rule_id are required"}

    try:
        client = get_client()
        rule = client.get(f"/api/v1/policies/{policy_id}/rules/{rule_id}")
        logger.info(f"[caller={caller}] Successfully retrieved rule {rule_id}")
        return rule
    except Exception as e:
        logger.error(f"[caller={caller}] Exception getting policy rule: {e}")
        return {"error": str(e)}
