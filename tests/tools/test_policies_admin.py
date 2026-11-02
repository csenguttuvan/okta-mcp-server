from unittest.mock import MagicMock, patch

MODULE = "okta_mcp_server.tools.policies.policies_admin"

MOCK_POLICY_ID = "00p1b2c3d4e5f6g7h8i9"
MOCK_RULE_ID = "0pr1b2c3d4e5f6g7h8i9"


def test_policies_admin_imports_real_get_caller_email():
    """Regression: this module used to define its own get_caller_email(ctx) that
    never read the ContextVar the middleware populates, so every log line here was
    attributed to 'unknown' regardless of who called it."""
    from okta_mcp_server.context import get_caller_email as real_get_caller_email
    from okta_mcp_server.tools.policies.policies_admin import get_caller_email as module_get_caller_email

    assert module_get_caller_email is real_get_caller_email


# ── delete_policy ─────────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_policy_not_confirmed_blocks(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"name": "Sign On Policy"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.policies.policies_admin import delete_policy

    result = delete_policy(policy_id=MOCK_POLICY_ID)
    assert "confirm_deletion=True" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_policy_confirmed_executes(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"name": "Sign On Policy"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.policies.policies_admin import delete_policy

    result = delete_policy(policy_id=MOCK_POLICY_ID, confirm_deletion=True)
    assert result["success"] is True
    client.delete.assert_called_once()


# ── delete_policy_rule ────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_policy_rule_not_confirmed_blocks(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"name": "Default Rule"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.policies.policies_admin import delete_policy_rule

    result = delete_policy_rule(policy_id=MOCK_POLICY_ID, rule_id=MOCK_RULE_ID)
    assert "confirm_deletion=True" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_policy_rule_confirmed_executes(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"name": "Default Rule"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.policies.policies_admin import delete_policy_rule

    result = delete_policy_rule(policy_id=MOCK_POLICY_ID, rule_id=MOCK_RULE_ID, confirm_deletion=True)
    assert result["success"] is True
    client.delete.assert_called_once()
