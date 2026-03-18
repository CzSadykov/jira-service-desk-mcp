# mcp-jira-service-desk

[![PyPI](https://img.shields.io/pypi/v/mcp-jira-service-desk)](https://pypi.org/project/mcp-jira-service-desk/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-jira-service-desk)](https://pypi.org/project/mcp-jira-service-desk/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

MCP (Model Context Protocol) server for **Jira Service Management** (formerly Jira Service Desk).  
Connects AI assistants — **Claude Code**, Claude Desktop, Cursor, and others — to your JSM instance via [Anthropic's MCP](https://modelcontextprotocol.io/).

Built on top of [`atlassian-python-api`](https://atlassian-python-api.readthedocs.io/service_desk.html) and inspired by [mcp-atlassian](https://github.com/sooperset/mcp-atlassian).

## Features

| Category | Tools |
|----------|-------|
| **Service Desks** | List desks, get desk by ID, app info |
| **Request Types** | List types, get type details, get required fields |
| **Customer Requests** | Create, get, list my requests, get status |
| **Comments** | Add public/internal comments, list, get by ID |
| **Customers** | Create customer, list, add/remove from desk |
| **Participants** | List, add, remove request participants |
| **Transitions** | List available transitions, perform transition |
| **Organizations** | CRUD organizations, manage users, link to desks |
| **Queues** | List queues, list issues in queue |
| **SLA** | Get SLA info per request, by metric ID |
| **Approvals** | List approvals, get by ID, approve/decline |
| **Attachments** | Upload temp file, attach to request |

**40 tools** total. Write operations are gated by `READ_ONLY_MODE`.

## Quick Start

### Install from PyPI

```bash
pip install mcp-jira-service-desk
```

Or with `uv`:

```bash
uv pip install mcp-jira-service-desk
```

Or install from source:

```bash
pip install -e .
```

### Configure

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

**Recommended shared format** (same env shape as `mcp-atlassian`):

```env
JIRA_URL=https://jira.your-company.com
JIRA_PERSONAL_TOKEN=<base64-encoded username:token>
```

Use a base64-encoded `username:token` string when you want one MCP config style
that works across both `mcp-atlassian` and `mcp-jira-service-desk` for
Atlassian Cloud. On non-Cloud/self-hosted Jira instances, `JIRA_PERSONAL_TOKEN`
now defaults to Bearer/PAT handling to avoid misclassifying base64-looking PATs.
If you intentionally need basic auth there, set `JIRA_PERSONAL_TOKEN_MODE=basic`.

**Alternative: Atlassian Cloud** (username + API token):

```env
JIRA_URL=https://your-instance.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

Generate an API token at https://id.atlassian.com/manage-profile/security/api-tokens.

**Alternative: Server / Data Center** (raw Personal Access Token):

```env
JIRA_URL=https://jira.your-company.com
JIRA_PERSONAL_TOKEN=your-personal-access-token
```

The token can be either a **raw PAT** (bearer token), the full
`Bearer <token>` header value, or a **base64-encoded `username:api_token`**
string. The server strips `Bearer` automatically when present.

For non-Cloud/self-hosted Jira, `JIRA_PERSONAL_TOKEN` is treated as Bearer/PAT
by default, even if it looks like base64. This avoids accidental fallback to
Basic auth for PATs that happen to decode cleanly. If you need to force Basic
auth from `JIRA_PERSONAL_TOKEN`, set:

```env
JIRA_PERSONAL_TOKEN_MODE=basic
```

> **Note:** `JIRA_IS_CLOUD` is auto-detected from the URL (`.atlassian.net` → Cloud).
> Set it explicitly only if the heuristic is wrong for your instance.

### Run

**stdio** (default — for Claude Code, Claude Desktop, Cursor, etc.):

```bash
mcp-jira-service-desk
```

**SSE** (for remote/web clients):

```bash
mcp-jira-service-desk --transport sse --port 8000
```

---

## Claude Code Integration

The fastest way to connect JSM to Claude Code:

```bash
claude mcp add jira-service-desk -- mcp-jira-service-desk
```

With environment variables inline:

```bash
claude mcp add jira-service-desk \
  -e JIRA_URL=https://jira.your-company.com \
  -e JIRA_PERSONAL_TOKEN=<base64-encoded username:token> \
  -- uvx mcp-jira-service-desk
```

To scope the server to your project only:

```bash
claude mcp add --scope project jira-service-desk \
  -e JIRA_URL=https://jira.your-company.com \
  -e JIRA_PERSONAL_TOKEN=<base64-encoded username:token> \
  -- uvx mcp-jira-service-desk
```

Verify it works:

```bash
claude mcp list
```

### Shared MCP Config

Add the same shape to `~/.claude.json`, project-level `.mcp.json`,
`claude_desktop_config.json`, or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mcp-atlassian": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://jira.your-company.com",
        "JIRA_PERSONAL_TOKEN": "<base64-encoded username:token>"
      }
    },
    "jira-service-desk": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-jira-service-desk"],
      "env": {
        "JIRA_URL": "https://jira.your-company.com",
        "JIRA_PERSONAL_TOKEN": "<base64-encoded username:token>"
      }
    }
  }
}
```

This mirrors the `mcp-atlassian` configuration style for Atlassian Cloud while
still allowing `mcp-jira-service-desk` to distinguish Cloud basic-auth tokens
from non-Cloud Bearer/PAT tokens.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_URL` | Yes | Jira instance URL |
| `JIRA_USERNAME` | Cloud | Email for Atlassian Cloud |
| `JIRA_API_TOKEN` | Cloud | API token for Cloud auth |
| `JIRA_PERSONAL_TOKEN` | Recommended | Raw PAT **or** base64-encoded `username:token` |
| `JIRA_PERSONAL_TOKEN_MODE` | No | `auto` (default), `pat`, or `basic` override for `JIRA_PERSONAL_TOKEN` |
| `JIRA_PASSWORD` | — | Basic auth password (not recommended) |
| `JIRA_IS_CLOUD` | No | Auto-detected from URL; set explicitly to override |
| `JIRA_SSL_VERIFY` | No | `true` (default) or `false` |
| `READ_ONLY_MODE` | No | `true` to disable all write operations |

## Available Tools

### Service Desks
- `get_service_desk_info` — Application info
- `list_service_desks` — All accessible service desks
- `get_service_desk` — Service desk by ID

### Request Types
- `list_request_types` — Request types for a desk
- `get_request_type` — Specific request type
- `get_request_type_fields` — Fields required for a request type

### Customer Requests
- `create_customer_request` — Create a new request
- `get_customer_request` — Get request by key
- `list_my_customer_requests` — Your requests
- `get_customer_request_status` — Request status

### Comments
- `add_request_comment` — Add public or internal comment
- `list_request_comments` — List comments on a request
- `get_request_comment` — Get comment by ID

### Customers
- `create_customer` — Create customer account
- `list_customers` — List customers of a desk
- `add_customers_to_service_desk` — Add customers
- `remove_customers_from_service_desk` — Remove customers

### Participants
- `list_request_participants` — List participants
- `add_request_participants` — Add participants
- `remove_request_participants` — Remove participants

### Transitions
- `list_customer_transitions` — Available transitions
- `perform_transition` — Execute a transition

### Organizations
- `list_organizations` — List organizations
- `get_organization` — Organization by ID
- `create_organization` — Create organization
- `delete_organization` — Delete organization
- `add_organization_to_service_desk` — Link org to desk
- `remove_organization_from_service_desk` — Unlink org
- `list_users_in_organization` — Users in org
- `add_users_to_organization` — Add users to org
- `remove_users_from_organization` — Remove users from org

### Queues
- `list_queues` — Queues in a service desk
- `list_issues_in_queue` — Issues in a queue

### SLA
- `get_request_sla` — SLA info for a request
- `get_request_sla_by_id` — Specific SLA metric

### Approvals
- `list_approvals` — Approvals for a request
- `get_approval` — Approval by ID
- `answer_approval` — Approve or decline

### Attachments
- `upload_temporary_attachment` — Upload temp file
- `attach_file_to_request` — Attach to request

## Architecture

```
src/mcp_jira_service_desk/
├── __init__.py      # CLI entry point (click)
├── __main__.py      # python -m support
├── config.py        # Environment-based configuration
├── client.py        # ServiceDeskClient — wraps atlassian-python-api
├── formatting.py    # Human-readable formatting for API responses
└── server.py        # FastMCP server with all tool definitions
```

- **config.py** — reads `JIRA_*` env vars, determines auth type
- **client.py** — thin typed wrapper around `atlassian.ServiceDesk`, normalizes paginated responses
- **formatting.py** — converts raw API dicts into markdown for LLM consumption
- **server.py** — `FastMCP` instance with `@mcp.tool()` decorators for each operation

## Development

```bash
git clone https://github.com/CzSadykov/mcp-jirasm.git
cd mcp-jirasm
pip install -e ".[dev]"
pytest
```

## License

MIT
