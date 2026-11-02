from unittest.mock import MagicMock, patch

MODULE = "okta_mcp_server.tools.groups.groups_admin"

MOCK_GROUP_ID = "00g1b2c3d4e5f6g7h8i9"
MOCK_USER_IDS = ["00u1b2c3d4e5f6g7h8i9", "00u2b2c3d4e5f6g7h8i9", "00u3b2c3d4e5f6g7h8i9"]


def make_client():
    client = MagicMock()
    client.put.return_value = None
    return client


def active_user(user_id):
    return {"status": "ACTIVE", "profile": {"email": f"{user_id}@example.com"}}


# ── add_users_to_group (live copy) ───────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_dry_run_default_makes_no_live_calls(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import add_users_to_group

    result = add_users_to_group(group_id=MOCK_GROUP_ID, user_ids=MOCK_USER_IDS)
    assert result["count"] == 3
    assert "DRY RUN" in result["message"]
    client.get.assert_not_called()
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_requires_confirm(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import add_users_to_group

    result = add_users_to_group(group_id=MOCK_GROUP_ID, user_ids=MOCK_USER_IDS, dry_run=False)
    assert result["success"] is False
    assert "confirm_add=True" in result["error"]
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_confirmed_executes(mock_get_client, _):
    client = make_client()
    client.get.side_effect = [active_user(uid) for uid in MOCK_USER_IDS]
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import add_users_to_group

    result = add_users_to_group(group_id=MOCK_GROUP_ID, user_ids=MOCK_USER_IDS, dry_run=False, confirm_add=True)
    assert result["success"] is True
    assert result["added"] == 3
    assert client.put.call_count == 3


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_exceeds_cap_blocked(mock_get_client, _):
    client = make_client()
    big_list = [f"00u{i:017d}" for i in range(60)]
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import add_users_to_group

    result = add_users_to_group(group_id=MOCK_GROUP_ID, user_ids=big_list, dry_run=False, confirm_add=True)
    assert result["success"] is False
    assert "exceeds the safety cap" in result["error"]
    client.get.assert_not_called()
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_override_cap_executes(mock_get_client, _):
    client = make_client()
    big_list = [f"00u{i:017d}" for i in range(60)]
    client.get.side_effect = [active_user(uid) for uid in big_list]
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import add_users_to_group

    result = add_users_to_group(
        group_id=MOCK_GROUP_ID, user_ids=big_list, dry_run=False, confirm_add=True, override_cap=True
    )
    assert result["success"] is True
    assert client.put.call_count == 60


# ── delete_group ──────────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_not_confirmed_blocks(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"profile": {"name": "Engineering"}, "type": "OKTA_GROUP"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import delete_group

    result = delete_group(group_id=MOCK_GROUP_ID)
    assert "confirm_deletion=True" in result
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_confirmed_executes(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"profile": {"name": "Engineering"}, "type": "OKTA_GROUP"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import delete_group

    result = delete_group(group_id=MOCK_GROUP_ID, confirm_deletion=True)
    assert "DELETED group" in result
    client.delete.assert_called_once()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_group_confirmed_but_built_in_blocks(mock_get_client, _):
    client = MagicMock()
    client.get.return_value = {"profile": {"name": "Everyone"}, "type": "BUILT_IN"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.groups.groups_admin import delete_group

    result = delete_group(group_id=MOCK_GROUP_ID, confirm_deletion=True)
    assert "Cannot delete built-in group" in result
    client.delete.assert_not_called()
