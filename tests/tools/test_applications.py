from unittest.mock import MagicMock, patch

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_client(get_return=None, post_return=None):
    client = MagicMock()
    client.get.return_value = get_return if get_return is not None else []
    client.post.return_value = post_return if post_return is not None else {}
    client.delete.return_value = None
    return client


MOCK_APP = {"id": "0oa1b2c3d4e5f6g7h8i9", "label": "Test App", "status": "ACTIVE", "signOnMode": "SAML_2_0"}
MOCK_USER = {"id": "00u1b2c3d4e5f6g7h8i9", "status": "ACTIVE", "profile": {"email": "test@example.com"}}


# ── list_applications ─────────────────────────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_applications_returns_formatted_string(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=[MOCK_APP])
    from okta_mcp_server.tools.applications.applications import list_applications

    result = list_applications()
    assert "Test App" in result
    assert "0oa1b2c3d4e5f6g7h8i9" in result


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_applications_empty(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=[])
    from okta_mcp_server.tools.applications.applications import list_applications

    result = list_applications()
    assert "No applications found" in result


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_applications_permission_error(mock_get_client, _):
    client = make_client()
    client.get.side_effect = PermissionError("Forbidden")
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications import list_applications

    result = list_applications()
    assert "Permission denied" in result


# ── get_application ───────────────────────────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_get_application_success(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=MOCK_APP)
    from okta_mcp_server.tools.applications.applications import get_application

    result = get_application(app_id="0oa1b2c3d4e5f6g7h8i9")
    assert result["id"] == "0oa1b2c3d4e5f6g7h8i9"


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_get_application_missing_id(mock_get_client, _):
    from okta_mcp_server.tools.applications.applications import get_application

    with pytest.raises(ValueError, match="app_id is required"):
        get_application(app_id="")


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_get_application_api_error(mock_get_client, _):
    client = make_client()
    client.get.side_effect = Exception("API error")
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications import get_application

    with pytest.raises(Exception, match="API error"):
        get_application(app_id="0oa1b2c3d4e5f6g7h8i9")


# ── list_application_users ────────────────────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_application_users_success(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=[MOCK_USER])
    from okta_mcp_server.tools.applications.applications import list_application_users

    result = list_application_users(app_id="0oa1b2c3d4e5f6g7h8i9")
    assert result["count"] == 1
    assert result["app_id"] == "0oa1b2c3d4e5f6g7h8i9"


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_application_users_missing_app_id(mock_get_client, _):
    from okta_mcp_server.tools.applications.applications import list_application_users

    with pytest.raises(ValueError, match="app_id is required"):
        list_application_users(app_id="")


# ── list_application_groups ───────────────────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_application_groups_success(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=[{"id": "grp1", "profile": {"name": "Admins"}}])
    from okta_mcp_server.tools.applications.applications import list_application_groups

    result = list_application_groups(app_id="0oa1b2c3d4e5f6g7h8i9")
    assert result["count"] == 1


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_list_application_groups_missing_app_id(mock_get_client, _):
    from okta_mcp_server.tools.applications.applications import list_application_groups

    with pytest.raises(ValueError, match="app_id is required"):
        list_application_groups(app_id="")


# ── find_application ──────────────────────────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_find_application_success(mock_get_client, _):
    mock_get_client.return_value = make_client(get_return=[MOCK_APP])
    from okta_mcp_server.tools.applications.applications import find_application

    result = find_application(names=["Test App"])
    assert "Test App" in result


@patch("okta_mcp_server.tools.applications.applications.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications.get_client")
def test_find_application_no_names(mock_get_client, _):
    from okta_mcp_server.tools.applications.applications import find_application

    result = find_application(names=[])
    assert "Please provide at least one" in result


# ── unassign_user_from_application (admin) ────────────────────────────────────


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_unassign_user_success(mock_get_client, _):
    client = MagicMock()
    client.get.side_effect = [MOCK_APP, MOCK_USER]
    client.delete.return_value = None
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import unassign_user_from_application

    result = unassign_user_from_application(app_id="0oa1b2c3d4e5f6g7h8i9", user_id="00u1b2c3d4e5f6g7h8i9")
    assert "unassigned" in result.lower()


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_unassign_user_invalid_app_id(mock_get_client, _):
    from okta_mcp_server.tools.applications.applications_admin import unassign_user_from_application

    result = unassign_user_from_application(app_id="bad-id", user_id="00u1b2c3d4e5f6g7h8i9")
    assert "❌" in result


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_unassign_user_api_error(mock_get_client, _):
    client = make_client()
    client.get.side_effect = Exception("Network error")
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import unassign_user_from_application

    result = unassign_user_from_application(app_id="0oa1b2c3d4e5f6g7h8i9", user_id="00u1b2c3d4e5f6g7h8i9")
    assert "❌" in result


# ── batch_assign_users_to_application ─────────────────────────────────────────


def _active_users(n):
    return [{"status": "ACTIVE", "profile": {"email": f"user{i}@example.com"}} for i in range(n)]


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_batch_assign_dry_run_default_makes_no_live_calls(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import batch_assign_users_to_application

    user_ids = ["00u1b2c3d4e5f6g7h8i9", "00u2b2c3d4e5f6g7h8i9"]
    result = batch_assign_users_to_application(app_id="0oa1b2c3d4e5f6g7h8i9", user_ids=user_ids)
    assert result["count"] == 2
    assert "DRY RUN" in result["message"]
    client.get.assert_not_called()
    client.post.assert_not_called()


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_batch_assign_requires_confirm(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import batch_assign_users_to_application

    user_ids = ["00u1b2c3d4e5f6g7h8i9"]
    result = batch_assign_users_to_application(app_id="0oa1b2c3d4e5f6g7h8i9", user_ids=user_ids, dry_run=False)
    assert result["success"] is False
    assert "confirm_assignment=True" in result["error"]
    client.post.assert_not_called()


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_batch_assign_confirmed_executes(mock_get_client, _):
    client = make_client()
    user_ids = ["00u1b2c3d4e5f6g7h8i9", "00u2b2c3d4e5f6g7h8i9"]
    client.get.side_effect = _active_users(len(user_ids))
    client.post.return_value = {"id": "assignment1"}
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import batch_assign_users_to_application

    result = batch_assign_users_to_application(
        app_id="0oa1b2c3d4e5f6g7h8i9", user_ids=user_ids, dry_run=False, confirm_assignment=True
    )
    assert result["success"] is True
    assert client.post.call_count == 2


@patch("okta_mcp_server.tools.applications.applications_admin.get_caller_email", return_value="ci@test.com")
@patch("okta_mcp_server.tools.applications.applications_admin.get_client")
def test_batch_assign_exceeds_cap_blocked(mock_get_client, _):
    client = make_client()
    mock_get_client.return_value = client
    from okta_mcp_server.tools.applications.applications_admin import batch_assign_users_to_application

    user_ids = [f"00u{i:017d}" for i in range(60)]
    result = batch_assign_users_to_application(
        app_id="0oa1b2c3d4e5f6g7h8i9", user_ids=user_ids, dry_run=False, confirm_assignment=True
    )
    assert result["success"] is False
    assert "exceeds the safety cap" in result["error"]
    client.get.assert_not_called()
    client.post.assert_not_called()
