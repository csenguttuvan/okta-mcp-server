from unittest.mock import MagicMock, patch

MODULE = "okta_mcp_server.tools.users.users_admin"

MOCK_USER_ID = "00u1b2c3d4e5f6g7h8i9"
MOCK_GROUP_ID = "00g1b2c3d4e5f6g7h8i9"
MOCK_APP_ID = "0oa1b2c3d4e5f6g7h8i9"


def make_client(get_return=None):
    client = MagicMock()
    client.get.return_value = get_return if get_return is not None else []
    client.post.return_value = {}
    client.put.return_value = {}
    client.delete.return_value = None
    return client


def make_matching_users(n, attribute="division", value="engineering"):
    return [
        {
            "id": f"00u{i:017d}",
            "status": "ACTIVE",
            "profile": {"email": f"user{i}@example.com", "firstName": "Test", "lastName": "User", attribute: value},
        }
        for i in range(n)
    ]


# ── deactivate_user ─────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_deactivate_user_not_confirmed_blocks(mock_get_client, _):
    client = make_client(get_return={"status": "ACTIVE", "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import deactivate_user

    result = deactivate_user(user_id=MOCK_USER_ID)
    assert "confirm_deactivation=True" in result
    client.post.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_deactivate_user_confirmed_executes(mock_get_client, _):
    client = make_client(get_return={"status": "ACTIVE", "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import deactivate_user

    result = deactivate_user(user_id=MOCK_USER_ID, confirm_deactivation=True)
    assert "deactivated" in result.lower()
    client.post.assert_called_once()


# ── reset_user_mfa_and_password ─────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_reset_user_mfa_and_password_not_confirmed_blocks(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import reset_user_mfa_and_password

    result = reset_user_mfa_and_password(user_id=MOCK_USER_ID)
    assert "confirm_reset=True" in result
    client.get.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_reset_user_mfa_and_password_confirmed_executes(mock_get_client, _):
    client = MagicMock()
    client.get.side_effect = [
        {"id": MOCK_USER_ID, "profile": {"email": "user@test.com"}},  # get user
        [],  # get factors
    ]
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import reset_user_mfa_and_password

    result = reset_user_mfa_and_password(user_id=MOCK_USER_ID, confirm_reset=True)
    assert "Reset completed" in result
    client.post.assert_called_once()


# ── reset_user_password ──────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_reset_user_password_not_confirmed_blocks(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import reset_user_password

    result = reset_user_password(user_id=MOCK_USER_ID)
    assert "confirm_reset=True" in result
    client.get.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_reset_user_password_confirmed_executes(mock_get_client, _):
    client = make_client(get_return={"id": MOCK_USER_ID, "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import reset_user_password

    result = reset_user_password(user_id=MOCK_USER_ID, confirm_reset=True)
    assert "Password reset email sent" in result
    client.post.assert_called_once()


# ── delete_user ──────────────────────────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_user_not_confirmed_blocks(mock_get_client, _):
    client = make_client(get_return={"status": "DEPROVISIONED", "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import delete_user

    result = delete_user(user_id=MOCK_USER_ID)
    assert "confirm_deletion=True" in result
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_user_confirmed_executes(mock_get_client, _):
    client = make_client(get_return={"status": "DEPROVISIONED", "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import delete_user

    result = delete_user(user_id=MOCK_USER_ID, confirm_deletion=True)
    assert "PERMANENTLY DELETED" in result
    client.delete.assert_called_once()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_delete_user_confirmed_but_not_deprovisioned_blocks(mock_get_client, _):
    client = make_client(get_return={"status": "ACTIVE", "profile": {"email": "user@test.com"}})
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import delete_user

    result = delete_user(user_id=MOCK_USER_ID, confirm_deletion=True)
    assert "must be DEPROVISIONED" in result
    client.delete.assert_not_called()


# ── add_users_to_group_by_attribute ─────────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_dry_run_default(mock_get_client, _):
    client = make_client(get_return=make_matching_users(3))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(attribute="division", value="engineering", group_id=MOCK_GROUP_ID)
    assert result["count"] == 3
    assert "DRY RUN" in result["message"]
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_requires_confirm(mock_get_client, _):
    client = make_client(get_return=make_matching_users(3))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False
    )
    assert result["success"] is False
    assert "confirm_add=True" in result["error"]
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_confirmed_executes(mock_get_client, _):
    client = make_client(get_return=make_matching_users(3))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False, confirm_add=True
    )
    assert result["success"] is True
    assert result["added"] == 3
    assert client.put.call_count == 3


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_exceeds_cap_blocked(mock_get_client, _):
    client = make_client(get_return=make_matching_users(60))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False, confirm_add=True
    )
    assert result["success"] is False
    assert "exceeds the safety cap" in result["error"]
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_exceeds_cap_dry_run_flags_it(mock_get_client, _):
    client = make_client(get_return=make_matching_users(60))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(attribute="division", value="engineering", group_id=MOCK_GROUP_ID)
    assert result["exceeds_cap"] is True
    client.put.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_add_users_to_group_by_attribute_override_cap_executes(mock_get_client, _):
    client = make_client(get_return=make_matching_users(60))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import add_users_to_group_by_attribute

    result = add_users_to_group_by_attribute(
        attribute="division",
        value="engineering",
        group_id=MOCK_GROUP_ID,
        dry_run=False,
        confirm_add=True,
        override_cap=True,
    )
    assert result["success"] is True
    assert client.put.call_count == 60


# ── unassign_users_from_application_by_attribute ────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_unassign_users_from_application_by_attribute_dry_run_default(mock_get_client, _):
    client = make_client(get_return=make_matching_users(4))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import unassign_users_from_application_by_attribute

    result = unassign_users_from_application_by_attribute(
        app_id=MOCK_APP_ID, attribute="division", value="engineering"
    )
    assert result["count"] == 4
    assert "DRY RUN" in result["message"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_unassign_users_from_application_by_attribute_requires_confirm(mock_get_client, _):
    client = make_client(get_return=make_matching_users(4))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import unassign_users_from_application_by_attribute

    result = unassign_users_from_application_by_attribute(
        app_id=MOCK_APP_ID, attribute="division", value="engineering", dry_run=False
    )
    assert result["success"] is False
    assert "confirm_removal=True" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_unassign_users_from_application_by_attribute_exceeds_cap_blocked(mock_get_client, _):
    client = make_client(get_return=make_matching_users(75))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import unassign_users_from_application_by_attribute

    result = unassign_users_from_application_by_attribute(
        app_id=MOCK_APP_ID, attribute="division", value="engineering", dry_run=False, confirm_removal=True
    )
    assert result["success"] is False
    assert "exceeds the safety cap" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_unassign_users_from_application_by_attribute_confirmed_executes(mock_get_client, _):
    client = make_client(get_return=make_matching_users(2))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import unassign_users_from_application_by_attribute

    result = unassign_users_from_application_by_attribute(
        app_id=MOCK_APP_ID, attribute="division", value="engineering", dry_run=False, confirm_removal=True
    )
    assert result["success"] is True
    assert result["removed"] == 2
    assert client.delete.call_count == 2


# ── remove_users_from_group_by_attribute ────────────────────────────────────────


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_remove_users_from_group_by_attribute_dry_run_default(mock_get_client, _):
    client = make_client(get_return=make_matching_users(3))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import remove_users_from_group_by_attribute

    result = remove_users_from_group_by_attribute(attribute="division", value="engineering", group_id=MOCK_GROUP_ID)
    assert result["count"] == 3
    assert "DRY RUN" in result["message"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_remove_users_from_group_by_attribute_requires_confirm(mock_get_client, _):
    client = make_client(get_return=make_matching_users(3))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import remove_users_from_group_by_attribute

    result = remove_users_from_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False
    )
    assert result["success"] is False
    assert "confirm_removal=True" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_remove_users_from_group_by_attribute_exceeds_cap_blocked(mock_get_client, _):
    client = make_client(get_return=make_matching_users(80))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import remove_users_from_group_by_attribute

    result = remove_users_from_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False, confirm_removal=True
    )
    assert result["success"] is False
    assert "exceeds the safety cap" in result["error"]
    client.delete.assert_not_called()


@patch(f"{MODULE}.get_caller_email", return_value="ci@test.com")
@patch(f"{MODULE}.get_client")
def test_remove_users_from_group_by_attribute_still_works_under_cap(mock_get_client, _):
    client = make_client(get_return=make_matching_users(2))
    mock_get_client.return_value = client
    from okta_mcp_server.tools.users.users_admin import remove_users_from_group_by_attribute

    result = remove_users_from_group_by_attribute(
        attribute="division", value="engineering", group_id=MOCK_GROUP_ID, dry_run=False, confirm_removal=True
    )
    assert result["success"] is True
    assert result["removed"] == 2
