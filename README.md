# Okta MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: >=3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Standard%20I%2FO-green.svg)](https://modelcontextprotocol.io/)

A production-grade [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that connects AI assistants like **Claude Desktop**, **Cursor**, and **Claude Code** to the Okta API.

Empower your LLMs to automate user provisioning, audit group memberships, troubleshoot access policies, query system logs, and inspect applications with built-in safety guardrails.

---

## ✨ Features

- **69+ Okta Tools**: Full coverage across Users, Groups, Applications, Policies, Group Rules, and System Logs.
- **Dual Authentication**:
  - **API Token (SSWS)**: Simple 30-second setup for individual developers and desktop AI clients.
  - **OAuth 2.0 Private Key JWT**: Enterprise-grade service app authentication with automatic token rotation.
- **Built-In Safety Guardrails**:
  - **Dry-run by default**: All bulk operations and attribute-based assignments preview changes before execution.
  - **Confirmation flags**: Single-target destructive actions (deactivation, deletion, MFA reset) require explicit `confirm_*` confirmation.
  - **Safety caps**: Prevents accidental mass updates (capped by default to 50 users unless explicitly overridden).
- **Flexible Modes**:
  - **Full Admin Mode**: Full read/write management across all tools.
  - **Read-Only Mode**: Safety-first mode that only exposes inspection and search tools (`OKTA_READ_ONLY=true`).
- **Standard I/O (`stdio`) & HTTP/SSE**: Runs natively as a subprocess inside your AI editor, or as a standalone container.

---

## 🚀 Quick Start

The fastest way to use Okta MCP server is with [`uv`](https://docs.astral.sh/uv/) / `uvx` without needing to install anything permanently.

### 1. Claude Desktop

Add the following to your Claude Desktop configuration file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "okta": {
      "command": "uvx",
      "args": ["okta-mcp-server"],
      "env": {
        "OKTA_API_BASE_URL": "https://your-org.okta.com",
        "OKTA_API_TOKEN": "00your_okta_api_token"
      }
    }
  }
}
```

### 2. Cursor

Add to `.cursor/mcp.json` in your project or global Cursor settings:

```json
{
  "mcpServers": {
    "okta": {
      "command": "uvx",
      "args": ["okta-mcp-server"],
      "env": {
        "OKTA_API_BASE_URL": "https://your-org.okta.com",
        "OKTA_API_TOKEN": "00your_okta_api_token"
      }
    }
  }
}
```

### 3. Claude Code CLI

Add Okta MCP server directly using the Claude Code CLI:

```bash
claude mcp add okta -- uvx okta-mcp-server \
  -e OKTA_API_BASE_URL="https://your-org.okta.com" \
  -e OKTA_API_TOKEN="00your_okta_api_token"
```

---

## 🔑 Authentication

### Method A: API Token (SSWS) — Recommended for Personal Use

1. Log in to your Okta Admin Console.
2. Navigate to **Security** → **API** → **Tokens**.
3. Click **Create Token**, name it (e.g. `claude-okta-mcp`), and copy the generated token.
4. Set the environment variables:
   ```bash
   OKTA_API_BASE_URL=https://your-org.okta.com
   OKTA_API_TOKEN=00your_api_token_here
   ```

### Method B: OAuth 2.0 Private Key JWT — For Teams & Enterprise

For zero static secrets, Okta supports service app authentication using public/private key pairs:

1. In Okta Admin Console, go to **Applications** → **Applications** → **Create App Integration**.
2. Select **API Services** and create an app.
3. Under **General** → **Client Credentials**, add a Public Key (PEM) and keep your private key (`private_key.pem`).
4. Under **Okta API Scopes**, grant the desired scopes (e.g., `okta.users.manage`, `okta.groups.manage`, `okta.apps.read`).
5. Configure your environment:
   ```bash
   OKTA_API_BASE_URL=https://your-org.okta.com
   OKTA_CLIENT_ID=0oayourclientid
   OKTA_PRIVATE_KEY_PATH=/path/to/private_key.pem
   OKTA_SCOPES="okta.users.manage okta.groups.manage okta.apps.manage okta.policies.manage okta.logs.read"
   ```

---

## 🛡️ Read-Only Mode

If you want your AI assistant to only inspect, audit, and troubleshoot without making any modifications:

Set `OKTA_READ_ONLY=true`:

```json
{
  "mcpServers": {
    "okta": {
      "command": "uvx",
      "args": ["okta-mcp-server"],
      "env": {
        "OKTA_API_BASE_URL": "https://your-org.okta.com",
        "OKTA_API_TOKEN": "00your_okta_api_token",
        "OKTA_READ_ONLY": "true"
      }
    }
  }
}
```

In read-only mode, all 44 state-mutating tools (`create_*`, `update_*`, `delete_*`, `assign_*`, `deactivate_*`) are disabled, and only the 25 inspection tools (`get_*`, `list_*`, `search_*`, `find_*`) are registered.

---

## 🧰 Available Tools Summary

| Category | Tools | Capabilities |
| :--- | :--- | :--- |
| **Users** | `find_user`, `get_user`, `list_users`, `search_users`, `search_users_fuzzy`, `search_users_by_attribute`, `create_user`, `update_user`, `deactivate_user`, `reactivate_user`, `delete_user`, `reset_user_password`, `reset_user_mfa_and_password` | Full user lifecycle, profile updates, credential resets, and fuzzy search |
| **Groups** | `get_group`, `list_groups`, `search_groups_fuzzy`, `list_group_users`, `get_user_groups`, `bulk_get_groups`, `create_group`, `update_group`, `delete_group`, `add_user_to_group`, `add_users_to_group`, `remove_user_from_group`, `add_users_to_group_by_attribute`, `remove_users_from_group_by_attribute` | Group administration, bulk membership automation, attribute matching |
| **Applications** | `find_application`, `get_application`, `list_applications`, `search_applications_fuzzy`, `list_application_users`, `list_application_groups`, `list_application_available_roles`, `search_aws_applications_by_account`, `create_application`, `assign_user_to_application`, `assign_group_to_application`, `assign_user_to_application_with_role`, `batch_assign_users_to_application`, `unassign_user_from_application`, `unassign_users_from_application_by_attribute` | SAML/OIDC/Bookmark apps, AWS IAM role assignments, bulk user provisioning |
| **Policies** | `get_policy`, `list_policies`, `get_policy_rule`, `list_policy_rules`, `create_policy`, `update_policy`, `activate_policy`, `deactivate_policy`, `delete_policy`, `create_policy_rule`, `update_policy_rule`, `activate_policy_rule`, `deactivate_policy_rule`, `delete_policy_rule` | Sign-on, MFA, Password, and Access policies |
| **Group Rules** | `get_group_rule`, `list_group_rules`, `create_group_rule`, `update_group_rule`, `activate_group_rule`, `deactivate_group_rule`, `delete_group_rule` | Dynamic, rule-based group membership automation |
| **System Logs** | `get_logs` | Real-time Okta audit log queries with filtering and time windows |

---

## 🐳 Docker Usage

A lightweight multi-platform Dockerfile is included:

```bash
docker build -t okta-mcp-server .
```

### Running stdio in Docker:

```bash
docker run -i --rm \
  -e OKTA_API_BASE_URL="https://your-org.okta.com" \
  -e OKTA_API_TOKEN="00your_token" \
  okta-mcp-server
```

### Running as an HTTP / SSE Server:

```bash
docker run -d --name okta-mcp \
  -p 8000:8000 \
  -e MCP_TRANSPORT="sse" \
  -e MCP_HOST="0.0.0.0" \
  -e MCP_PORT="8000" \
  -e OKTA_API_BASE_URL="https://your-org.okta.com" \
  -e OKTA_API_TOKEN="00your_token" \
  okta-mcp-server
```

---

## 🧪 Development & Testing

Clone the repository and install dependencies with [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/csenguttuvan/okta-mcp-server.git
cd okta-mcp-server
uv sync

# Run the test suite
uv run pytest -v

# Run lint and code checks
uv run ruff check .
uv run ruff format --check .
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
