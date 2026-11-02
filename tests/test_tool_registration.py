"""
Regression test for the duplicate `add_users_to_group` tool registration bug:
users_admin.py and groups_admin.py both defined a function named add_users_to_group
decorated with @mcp.tool() — FastMCP silently let the later import win (just logs a
warning), so half the codebase was calling dead code without realizing it.

Note: a broader sweep found several other read-only/admin file pairs (e.g.
list_policies, get_policy, get_application, get_group) with the same pattern —
that's a separate, pre-existing issue out of scope for this guardrails change and
is intentionally not asserted against here. This test is scoped to the specific
duplicate that was fixed.
"""

import ast
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent / "src" / "okta_mcp_server" / "tools"


def _is_mcp_tool_decorator(decorator: ast.expr) -> bool:
    # Matches both `@mcp.tool()` and `@mcp.tool(...)`
    if isinstance(decorator, ast.Call):
        decorator = decorator.func
    return isinstance(decorator, ast.Attribute) and decorator.attr == "tool"


def _collect_tool_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_is_mcp_tool_decorator(d) for d in node.decorator_list):
                names.append(node.name)
    return names


def test_add_users_to_group_is_registered_exactly_once():
    files_defining_it = [
        str(path.relative_to(TOOLS_DIR.parent.parent.parent))
        for path in TOOLS_DIR.rglob("*.py")
        if path.name != "__init__.py" and "add_users_to_group" in _collect_tool_names(path)
    ]

    assert files_defining_it == ["src/okta_mcp_server/tools/groups/groups_admin.py"], (
        f"add_users_to_group should be defined exactly once (in groups_admin.py) — found in: {files_defining_it}"
    )
