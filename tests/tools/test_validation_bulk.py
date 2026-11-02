from okta_mcp_server.utils.validation import check_bulk_size

# ── check_bulk_size ────────────────────────────────────────────────────────────


def test_check_bulk_size_under_cap():
    is_valid, error = check_bulk_size(5, max_targets=50)
    assert is_valid is True
    assert error is None


def test_check_bulk_size_at_cap():
    is_valid, error = check_bulk_size(50, max_targets=50)
    assert is_valid is True
    assert error is None


def test_check_bulk_size_over_cap_rejected():
    is_valid, error = check_bulk_size(51, max_targets=50)
    assert is_valid is False
    assert "51" in error
    assert "50" in error
    assert "override_cap" in error


def test_check_bulk_size_over_cap_with_override():
    is_valid, error = check_bulk_size(900, override_cap=True, max_targets=50)
    assert is_valid is True
    assert error is None


def test_check_bulk_size_default_max_targets():
    # Uses the module-level MAX_BULK_TARGETS default (50 unless OKTA_MAX_BULK_TARGETS is set)
    is_valid, error = check_bulk_size(10)
    assert is_valid is True
    assert error is None
