from unittest.mock import MagicMock, patch

MODULE = "okta_mcp_server.tools.rules.group_rules"

MOCK_RULE_ID = "0pr1b2c3d4e5f6g7h8i9"


def make_client():
    client = MagicMock()
    client.delete.return_value = None
    return client


# ── get_caller_email wiring ──────────────────────────────────────────────────────


def test_group_rules_imports_real_get_caller_email():
    """Regression: this module used to define its own get_caller_email(ctx) that
    never read the ContextVar the middleware populates, so every log line here was
    attributed to 'unknown' regardless of who called it."""
    from okta_mcp_server.context import get_caller_email as real_get_caller_email
    from okta_mcp_server.tools.rules.group_rules import get_caller_email as module_get_caller_email

    assert module_get_caller_email is real_get_caller_email


# ── delete_group_rule ────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_rule_not_confirmed_blocks(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.rules.group_rules import delete_group_rule

    result = delete_group_rule(rule_id=MOCK_RULE_ID)
    assert "confirm_deletion=True" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_rule_confirmed_executes(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.rules.group_rules import delete_group_rule

    result = delete_group_rule(rule_id=MOCK_RULE_ID, confirm_deletion=True)
    assert result["success"] is True
    client.delete.assert_called_once()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_rule_missing_rule_id(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.rules.group_rules import delete_group_rule

    result = delete_group_rule(rule_id="", confirm_deletion=True)
    assert "rule_id is required" in result["error"]
    client.delete.assert_not_called()
