from typing import Any, Dict, Optional

from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.context import get_caller_email
from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.oauth_jwt_client import get_client
from okta_mcp_server.utils.validation import validate_boolean


@mcp.tool()
def list_group_rules(
    ctx: Context | None = None,
    limit: Optional[int] = 20,
    after: Optional[str] = None,
    search: Optional[str] = None,
    expand: Optional[str] = None,
) -> Dict[str, Any]:
    """List all group rules in the Okta organization.

    Parameters:
        limit (int, optional): Number of results to return (max 200).
        after (str, optional): Specifies the pagination cursor for the next page of rules.
        search (str, optional): Filters rules by name.
        expand (str, optional): If set to "groupIdToGroupNameMap", returns group names in the response.

    Returns:
        Dict containing:
            - rules (List[Dict]): List of group rule dictionaries
            - error (str): Error message if the operation fails
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Listing group rules from Okta organization")

    try:
        client = get_client()
        params = {"limit": limit}
        if after:
            params["after"] = after
        if search:
            params["search"] = search
        if expand:
            params["expand"] = expand

        rules = client.get("/api/v1/groups/rules", params=params)

        if not rules:
            logger.info(f"[caller={caller}] No group rules found")
            return {"rules": []}

        logger.info(f"[caller={caller}] Successfully retrieved {len(rules)} group rules")
        return {"rules": rules}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception listing group rules: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_group_rule(
    ctx: Context | None = None, rule_id: str = "", expand: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve a specific group rule.

    Parameters:
        rule_id (str, required): The ID of the group rule.
        expand (str, optional): If set to "groupIdToGroupNameMap", returns group names in the response.

    Returns:
        Dict containing the group rule details.
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Getting group rule: {rule_id}")

    if not rule_id:
        logger.error(f"[caller={caller}] rule_id is required")
        return {"error": "rule_id is required"}

    try:
        client = get_client()
        params = {"expand": expand} if expand else None
        rule = client.get(f"/api/v1/groups/rules/{rule_id}", params=params)
        logger.info(f"[caller={caller}] Successfully retrieved group rule {rule_id}")
        return rule
    except Exception as e:
        logger.error(f"[caller={caller}] Exception getting group rule: {e}")
        return {"error": str(e)}


@mcp.tool()
def create_group_rule(
    ctx: Context | None = None, rule_data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Create a new group rule for dynamic, expression-based group membership.

    Parameters:
        rule_data (dict, required): The group rule configuration containing:
            - name (str, required): Rule name
            - type (str, optional): Rule type, defaults to "group_rule"
            - conditions (dict, required): Must contain an expression, e.g.
              {"expression": {"type": "urn:okta:expression:1.0", "value": "user.department==\"Sales\""}}
            - actions (dict, required): Must contain the target group(s), e.g.
              {"assignUserToGroups": {"groupIds": ["<group_id>"]}}

    Returns:
        Dict containing the created group rule details. New rules are created INACTIVE
        by default; call activate_group_rule to start evaluating and assigning members.
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Creating group rule")

    if not rule_data:
        logger.error(f"[caller={caller}] rule_data is required")
        return {"error": "rule_data is required"}

    rule_data.setdefault("type", "group_rule")

    try:
        client = get_client()
        rule = client.post("/api/v1/groups/rules", data=rule_data)
        logger.info(f"[caller={caller}] Created group rule: {rule.get('id', 'N/A')}")
        return rule
    except Exception as e:
        logger.error(f"[caller={caller}] Exception creating group rule: {e}")
        return {"error": str(e)}


@mcp.tool()
def update_group_rule(
    ctx: Context | None = None, rule_id: str = "", rule_data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Update an existing group rule.

    Note: Okta requires the rule to be INACTIVE before it can be updated —
    call deactivate_group_rule first if the rule is currently active.

    Parameters:
        rule_id (str, required): The ID of the group rule to update.
        rule_data (dict, required): The updated group rule configuration.

    Returns:
        Dict containing the updated group rule details.
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Updating group rule: {rule_id}")

    if not rule_id or not rule_data:
        logger.error(f"[caller={caller}] rule_id and rule_data are required")
        return {"error": "rule_id and rule_data are required"}

    try:
        client = get_client()
        rule = client.put(f"/api/v1/groups/rules/{rule_id}", data=rule_data)
        logger.info(f"[caller={caller}] Updated group rule: {rule_id}")
        return rule
    except Exception as e:
        logger.error(f"[caller={caller}] Exception updating group rule: {e}")
        return {"error": str(e)}


@mcp.tool()
def delete_group_rule(
    ctx: Context | None = None,
    rule_id: str = "",
    remove_users: bool = False,
    confirm_deletion: bool = False,
) -> Dict[str, Any]:
    """Delete a group rule.

    Note: Okta requires the rule to be INACTIVE before it can be deleted —
    call deactivate_group_rule first if the rule is currently active.

    Parameters:
        rule_id (str, required): The ID of the group rule to delete.
        remove_users (bool, optional): If True, also removes users the rule had
            assigned to the target group(s). Defaults to False.
        confirm_deletion (bool, required): Must be True to proceed.

    Returns:
        Dict with success status.
    """
    caller = get_caller_email()

    if not rule_id:
        logger.error(f"[caller={caller}] rule_id is required")
        return {"error": "rule_id is required"}

    is_valid, error = validate_boolean(confirm_deletion, required=True, field_name="confirm_deletion")
    if not is_valid:
        return {"error": error}

    if not confirm_deletion:
        return {"error": "❌ Set confirm_deletion=True to proceed. ⚠️ This permanently removes the group rule."}

    logger.warning(f"AUDIT: Group rule deletion | caller={caller} | rule_id={rule_id} | remove_users={remove_users}")

    try:
        client = get_client()
        params = {"removeUsers": str(remove_users).lower()}
        client.delete(f"/api/v1/groups/rules/{rule_id}", params=params)
        logger.info(f"[caller={caller}] Deleted group rule: {rule_id}")
        return {"success": True, "message": f"Group rule {rule_id} deleted successfully"}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception deleting group rule: {e}")
        return {"error": str(e)}


@mcp.tool()
def activate_group_rule(ctx: Context | None = None, rule_id: str = "") -> Dict[str, Any]:
    """Activate a group rule so Okta starts evaluating it and assigning matching users.

    Parameters:
        rule_id (str, required): The ID of the group rule to activate.

    Returns:
        Dict with success status.
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Activating group rule: {rule_id}")

    if not rule_id:
        logger.error(f"[caller={caller}] rule_id is required")
        return {"error": "rule_id is required"}

    try:
        client = get_client()
        client.post(f"/api/v1/groups/rules/{rule_id}/lifecycle/activate")
        logger.info(f"[caller={caller}] Activated group rule: {rule_id}")
        return {"success": True, "message": f"Group rule {rule_id} activated successfully"}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception activating group rule: {e}")
        return {"error": str(e)}


@mcp.tool()
def deactivate_group_rule(ctx: Context | None = None, rule_id: str = "") -> Dict[str, Any]:
    """Deactivate a group rule. Required before it can be updated or deleted.

    Parameters:
        rule_id (str, required): The ID of the group rule to deactivate.

    Returns:
        Dict with success status.
    """
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Deactivating group rule: {rule_id}")

    if not rule_id:
        logger.error(f"[caller={caller}] rule_id is required")
        return {"error": "rule_id is required"}

    try:
        client = get_client()
        client.post(f"/api/v1/groups/rules/{rule_id}/lifecycle/deactivate")
        logger.info(f"[caller={caller}] Deactivated group rule: {rule_id}")
        return {"success": True, "message": f"Group rule {rule_id} deactivated successfully"}
    except Exception as e:
        logger.error(f"[caller={caller}] Exception deactivating group rule: {e}")
        return {"error": str(e)}
