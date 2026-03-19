"""MCP server for Jira Service Desk (Service Management)."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from .client import ServiceDeskClient
from .config import ServiceDeskConfig
from .formatting import (
    format_approval,
    format_approval_list,
    format_comment,
    format_comment_list,
    format_customer_list,
    format_customer_request,
    format_customer_request_list,
    format_json,
    format_organization,
    format_organization_list,
    format_participant_list,
    format_queue_issue_list,
    format_queue_list,
    format_request_type,
    format_request_type_fields,
    format_request_type_list,
    format_service_desk,
    format_service_desk_list,
    format_sla,
    format_sla_list,
    format_transition_list,
)

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    client: ServiceDeskClient
    config: ServiceDeskConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Initialize ServiceDeskClient on startup."""
    config = ServiceDeskConfig.from_env()
    client = ServiceDeskClient(config)
    logger.info("Connected to Jira Service Desk at %s", config.url)
    yield AppContext(client=client, config=config)


def _get_client(ctx: Context) -> ServiceDeskClient:
    return ctx.request_context.lifespan_context.client


def _get_config(ctx: Context) -> ServiceDeskConfig:
    return ctx.request_context.lifespan_context.config


def _check_write(ctx: Context) -> None:
    config = _get_config(ctx)
    if config.read_only:
        raise ValueError(
            "Server is in read-only mode (READ_ONLY_MODE=true). "
            "Write operations are disabled."
        )


def _handle_error(e: Exception) -> str:
    logger.exception("Tool error")
    return f"Error: {e}"


mcp = FastMCP(
    "Jira Service Desk",
    instructions=(
        "MCP server for Jira Service Management (Service Desk). "
        "Provides tools to manage service desks, customer requests, "
        "comments, customers, organizations, queues, SLA, approvals, "
        "and transitions."
    ),
    lifespan=app_lifespan,
)

# ======================================================================
# Service Desk Info
# ======================================================================


@mcp.tool()
async def get_service_desk_info(ctx: Context) -> str:
    """Get information about the Jira Service Management application.

    Returns version and other runtime details of the JSM instance.
    Use this to verify connectivity and check the installed JSM version.
    """
    try:
        client = _get_client(ctx)
        info = client.get_info()
        return format_json(info)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_service_desks(ctx: Context) -> str:
    """List all service desks accessible to the current user.

    Returns IDs, project keys and names of every service desk the
    authenticated user can see. Use this as a starting point to discover
    available service desks before querying request types, queues, etc.
    """
    try:
        client = _get_client(ctx)
        desks = client.get_service_desks()
        return format_service_desk_list(desks)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_service_desk(ctx: Context, service_desk_id: str) -> str:
    """Get details of a specific service desk by its numeric ID.

    Use ``list_service_desks`` first to find the ID.

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
    """
    try:
        client = _get_client(ctx)
        desk = client.get_service_desk_by_id(service_desk_id)
        return format_service_desk(desk)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Request Types
# ======================================================================


@mcp.tool()
async def list_request_types(ctx: Context, service_desk_id: str) -> str:
    """List all request types available in a service desk.

    Each request type defines a form that customers fill in when raising a
    request (e.g. "Report a bug", "Request access").  Use this to discover
    which request types are available before creating a customer request.

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
    """
    try:
        client = _get_client(ctx)
        types = client.get_request_types(service_desk_id)
        return format_request_type_list(types)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_request_type(
    ctx: Context, service_desk_id: str, request_type_id: str
) -> str:
    """Get details of a specific request type (name, description, help text).

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
        request_type_id: The numeric ID of the request type (e.g. "10").
    """
    try:
        client = _get_client(ctx)
        rt = client.get_request_type(service_desk_id, request_type_id)
        return format_request_type(rt)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_request_type_fields(
    ctx: Context, service_desk_id: str, request_type_id: str
) -> str:
    """Get the fields required to create a request of this type.

    **Always call this before ``create_customer_request``** to learn which
    fields are required, their IDs, and valid values.

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
        request_type_id: The numeric ID of the request type (e.g. "10").
    """
    try:
        client = _get_client(ctx)
        fields = client.get_request_type_fields(service_desk_id, request_type_id)
        return format_request_type_fields(fields)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Customer Requests
# ======================================================================


@mcp.tool()
async def create_customer_request(
    ctx: Context,
    service_desk_id: str,
    request_type_id: str,
    values_json: str,
    raise_on_behalf_of: str = "",
    request_participants: str = "",
) -> str:
    """Create a new customer request (ticket) in a service desk.

    **Tip:** call ``get_request_type_fields`` first to discover required
    field IDs and valid values for the chosen request type.

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
        request_type_id: The numeric ID of the request type (e.g. "10").
        values_json: JSON object with field values.
            Example: ``{"summary": "VPN not working", "description": "Cannot connect since morning"}``
        raise_on_behalf_of: (Optional) Account ID (Cloud) or username
            (Server/DC) to raise the request on behalf of another user.
        request_participants: (Optional) Comma-separated account IDs or
            usernames to add as request participants.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        values = json.loads(values_json)
        participants = (
            [p.strip() for p in request_participants.split(",") if p.strip()]
            if request_participants
            else None
        )
        result = client.create_customer_request(
            service_desk_id=service_desk_id,
            request_type_id=request_type_id,
            values=values,
            raise_on_behalf_of=raise_on_behalf_of or None,
            request_participants=participants,
        )
        return format_customer_request(result)
    except json.JSONDecodeError:
        return "Error: values_json must be a valid JSON string."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_customer_request(ctx: Context, issue_id_or_key: str) -> str:
    """Get full details of a customer request including status, reporter, and field values.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
    """
    try:
        client = _get_client(ctx)
        req = client.get_customer_request(issue_id_or_key)
        return format_customer_request(req)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_my_customer_requests(ctx: Context) -> str:
    """List customer requests raised by or involving the current user.

    Returns requests where the authenticated user is the reporter or a
    participant. Useful to see "my open tickets" at a glance.
    """
    try:
        client = _get_client(ctx)
        requests = client.get_my_customer_requests()
        return format_customer_request_list(requests)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_customer_request_status(ctx: Context, issue_id_or_key: str) -> str:
    """Get the current status and status category of a customer request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
    """
    try:
        client = _get_client(ctx)
        status = client.get_customer_request_status(issue_id_or_key)
        return format_json(status)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Comments
# ======================================================================


@mcp.tool()
async def add_request_comment(
    ctx: Context, issue_id_or_key: str, body: str, public: bool = True
) -> str:
    """Add a comment to a customer request.

    Set ``public=true`` for customer-visible replies or ``public=false``
    for internal agent notes that the customer cannot see.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        body: The comment text (plain text or Jira wiki markup).
        public: ``true`` — visible to customer; ``false`` — internal agent note.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        comment = client.create_request_comment(issue_id_or_key, body, public=public)
        return format_comment(comment)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_request_comments(
    ctx: Context,
    issue_id_or_key: str,
    public: bool = True,
    internal: bool = True,
    start: int = 0,
    limit: int = 50,
) -> str:
    """List comments on a customer request with filtering by visibility.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        public: Include public (customer-visible) comments.
        internal: Include internal (agent-only) comments.
        start: Pagination offset (0-based).
        limit: Maximum number of comments to return (default 50).
    """
    try:
        client = _get_client(ctx)
        comments = client.get_request_comments(
            issue_id_or_key, start=start, limit=limit, public=public, internal=internal
        )
        return format_comment_list(comments)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_request_comment(
    ctx: Context, issue_id_or_key: str, comment_id: str
) -> str:
    """Get a single comment by its ID.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        comment_id: The numeric comment ID.
    """
    try:
        client = _get_client(ctx)
        comment = client.get_request_comment_by_id(issue_id_or_key, comment_id)
        return format_comment(comment)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Customers
# ======================================================================


@mcp.tool()
async def create_customer(ctx: Context, full_name: str, email: str) -> str:
    """Create a new customer account in the JSM instance (experimental API).

    The customer will be able to raise requests through the customer portal.

    Args:
        full_name: The customer's display name (e.g. "Jane Doe").
        email: The customer's email address.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.create_customer(full_name, email)
        return format_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_customers(
    ctx: Context,
    service_desk_id: str,
    query: str = "",
    start: int = 0,
    limit: int = 50,
) -> str:
    """List customers who have access to a service desk.

    Optionally filter by name or email substring.

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
        query: (Optional) Filter string — matches against display name and
            email address.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        customers = client.get_customers(
            service_desk_id, query=query or None, start=start, limit=limit
        )
        return format_customer_list(customers)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def add_customers_to_service_desk(
    ctx: Context,
    service_desk_id: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Grant one or more users access to a service desk as customers.

    Provide **usernames** for Server/Data Center or **account_ids** for Cloud.

    Args:
        service_desk_id: The numeric ID of the service desk.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        client.add_customers(service_desk_id, usernames=unames, account_ids=aids)
        return "Customers added successfully."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def remove_customers_from_service_desk(
    ctx: Context,
    service_desk_id: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Revoke customer access from a service desk.

    Provide **usernames** for Server/Data Center or **account_ids** for Cloud.

    Args:
        service_desk_id: The numeric ID of the service desk.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        client.remove_customers(service_desk_id, usernames=unames, account_ids=aids)
        return "Customers removed successfully."
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Participants
# ======================================================================


@mcp.tool()
async def list_request_participants(
    ctx: Context, issue_id_or_key: str, start: int = 0, limit: int = 50
) -> str:
    """List users who participate in (watch) a customer request.

    Participants receive notifications about request updates.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        participants = client.get_request_participants(
            issue_id_or_key, start=start, limit=limit
        )
        return format_participant_list(participants)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def add_request_participants(
    ctx: Context,
    issue_id_or_key: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Add participants to a customer request so they receive updates.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        result = client.add_request_participants(
            issue_id_or_key, usernames=unames, account_ids=aids
        )
        return format_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def remove_request_participants(
    ctx: Context,
    issue_id_or_key: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Remove participants from a customer request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        result = client.remove_request_participants(
            issue_id_or_key, usernames=unames, account_ids=aids
        )
        return format_json(result)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Transitions
# ======================================================================


@mcp.tool()
async def list_customer_transitions(ctx: Context, issue_id_or_key: str) -> str:
    """List transitions available for a customer request in its current status.

    Use the returned transition IDs with ``perform_transition``.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
    """
    try:
        client = _get_client(ctx)
        transitions = client.get_customer_transitions(issue_id_or_key)
        return format_transition_list(transitions)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def perform_transition(
    ctx: Context, issue_id_or_key: str, transition_id: str, comment: str = ""
) -> str:
    """Perform a workflow transition on a customer request (e.g. resolve, close).

    Call ``list_customer_transitions`` first to discover available transition IDs.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        transition_id: The numeric transition ID.
        comment: (Optional) Comment to add along with the transition.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.perform_transition(
            issue_id_or_key, transition_id, comment=comment or None
        )
        return f"Transition performed successfully.\n{format_json(result) if result else ''}"
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Organizations
# ======================================================================


@mcp.tool()
async def list_organizations(
    ctx: Context,
    service_desk_id: str = "",
    start: int = 0,
    limit: int = 50,
) -> str:
    """List organizations, optionally scoped to a specific service desk.

    Organizations group customers for easier access management.

    Args:
        service_desk_id: (Optional) Limit results to organizations linked
            to this service desk.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        orgs = client.get_organizations(
            service_desk_id=service_desk_id or None, start=start, limit=limit
        )
        return format_organization_list(orgs)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_organization(ctx: Context, organization_id: str) -> str:
    """Get details of a specific organization by its ID.

    Args:
        organization_id: The numeric organization ID.
    """
    try:
        client = _get_client(ctx)
        org = client.get_organization(organization_id)
        return format_organization(org)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def create_organization(ctx: Context, name: str) -> str:
    """Create a new customer organization.

    Args:
        name: The display name for the new organization.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.create_organization(name)
        return format_organization(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def delete_organization(ctx: Context, organization_id: str) -> str:
    """Permanently delete an organization and remove all its member associations.

    Args:
        organization_id: The numeric organization ID.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        client.delete_organization(organization_id)
        return f"Organization {organization_id} deleted successfully."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def add_organization_to_service_desk(
    ctx: Context, service_desk_id: str, organization_id: int
) -> str:
    """Link an organization to a service desk so its members can raise requests.

    Args:
        service_desk_id: The numeric ID of the service desk.
        organization_id: The numeric organization ID.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        client.add_organization(service_desk_id, organization_id)
        return f"Organization {organization_id} added to service desk {service_desk_id}."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def remove_organization_from_service_desk(
    ctx: Context, service_desk_id: str, organization_id: int
) -> str:
    """Unlink an organization from a service desk.

    Args:
        service_desk_id: The numeric ID of the service desk.
        organization_id: The numeric organization ID.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        client.remove_organization(service_desk_id, organization_id)
        return f"Organization {organization_id} removed from service desk {service_desk_id}."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_users_in_organization(
    ctx: Context, organization_id: str, start: int = 0, limit: int = 50
) -> str:
    """List users who belong to an organization.

    Args:
        organization_id: The numeric organization ID.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        users = client.get_users_in_organization(organization_id, start=start, limit=limit)
        return format_customer_list(users)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def add_users_to_organization(
    ctx: Context,
    organization_id: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Add users to an organization.

    Provide **usernames** for Server/Data Center or **account_ids** for Cloud.

    Args:
        organization_id: The numeric organization ID.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        client.add_users_to_organization(
            organization_id, usernames=unames, account_ids=aids
        )
        return f"Users added to organization {organization_id}."
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def remove_users_from_organization(
    ctx: Context,
    organization_id: str,
    usernames: str = "",
    account_ids: str = "",
) -> str:
    """Remove users from an organization.

    Provide **usernames** for Server/Data Center or **account_ids** for Cloud.

    Args:
        organization_id: The numeric organization ID.
        usernames: (Optional) Comma-separated usernames (Server/DC).
        account_ids: (Optional) Comma-separated Atlassian account IDs (Cloud).
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        unames = [u.strip() for u in usernames.split(",") if u.strip()] if usernames else None
        aids = [a.strip() for a in account_ids.split(",") if a.strip()] if account_ids else None
        client.remove_users_from_organization(
            organization_id, usernames=unames, account_ids=aids
        )
        return f"Users removed from organization {organization_id}."
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Queues
# ======================================================================


@mcp.tool()
async def list_queues(
    ctx: Context,
    service_desk_id: str,
    include_count: bool = False,
    start: int = 0,
    limit: int = 50,
) -> str:
    """List agent queues defined in a service desk.

    Queues are saved JQL filters that agents use to triage requests
    (e.g. "All open", "Unassigned", "SLA breached").

    Args:
        service_desk_id: The numeric ID of the service desk (e.g. "1").
        include_count: Set ``true`` to include the number of issues per queue.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        queues = client.get_queues(
            service_desk_id, include_count=include_count, start=start, limit=limit
        )
        return format_queue_list(queues)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def list_issues_in_queue(
    ctx: Context,
    service_desk_id: str,
    queue_id: str,
    start: int = 0,
    limit: int = 50,
) -> str:
    """List customer requests currently sitting in a specific queue.

    Use ``list_queues`` first to discover queue IDs.

    Args:
        service_desk_id: The numeric ID of the service desk.
        queue_id: The numeric queue ID.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        issues = client.get_issues_in_queue(
            service_desk_id, queue_id, start=start, limit=limit
        )
        return format_queue_issue_list(issues)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# SLA
# ======================================================================


@mcp.tool()
async def get_request_sla(
    ctx: Context, issue_id_or_key: str, start: int = 0, limit: int = 50
) -> str:
    """Get SLA (Service Level Agreement) metrics for a customer request.

    Returns remaining time, breach status, and goal durations for every
    SLA metric configured on the request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        sla_list = client.get_sla(issue_id_or_key, start=start, limit=limit)
        return format_sla_list(sla_list)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_request_sla_by_id(
    ctx: Context, issue_id_or_key: str, sla_id: str
) -> str:
    """Get a specific SLA metric by its ID for a customer request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        sla_id: The SLA metric ID.
    """
    try:
        client = _get_client(ctx)
        sla = client.get_sla_by_id(issue_id_or_key, sla_id)
        return format_sla(sla)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Approvals
# ======================================================================


@mcp.tool()
async def list_approvals(
    ctx: Context, issue_id_or_key: str, start: int = 0, limit: int = 50
) -> str:
    """List pending and completed approvals for a customer request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        start: Pagination offset (0-based).
        limit: Maximum number of results (default 50).
    """
    try:
        client = _get_client(ctx)
        approvals = client.get_approvals(issue_id_or_key, start=start, limit=limit)
        return format_approval_list(approvals)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def get_approval(
    ctx: Context, issue_id_or_key: str, approval_id: str
) -> str:
    """Get details of a specific approval including approver decisions.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        approval_id: The numeric approval ID.
    """
    try:
        client = _get_client(ctx)
        approval = client.get_approval_by_id(issue_id_or_key, approval_id)
        return format_approval(approval)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def answer_approval(
    ctx: Context, issue_id_or_key: str, approval_id: str, decision: str
) -> str:
    """Approve or decline an approval request.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        approval_id: The numeric approval ID.
        decision: ``"approve"`` or ``"decline"``.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.answer_approval(issue_id_or_key, approval_id, decision)
        return format_approval(result)
    except Exception as e:
        return _handle_error(e)


# ======================================================================
# Attachments
# ======================================================================


@mcp.tool()
async def upload_temporary_attachment(
    ctx: Context, service_desk_id: str, filename: str
) -> str:
    """Upload a file as a temporary attachment.

    The returned temporary attachment ID must then be passed to
    ``attach_file_to_request`` to permanently attach it to a request.

    Args:
        service_desk_id: The numeric ID of the service desk.
        filename: Absolute path to the file on the server filesystem.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.attach_temporary_file(service_desk_id, filename)
        return format_json(result)
    except Exception as e:
        return _handle_error(e)


@mcp.tool()
async def attach_file_to_request(
    ctx: Context,
    issue_id_or_key: str,
    temp_attachment_id: str,
    public: bool = True,
    comment: str = "",
) -> str:
    """Attach a previously uploaded temporary file to a customer request.

    Call ``upload_temporary_attachment`` first to obtain the temporary ID.

    Args:
        issue_id_or_key: The issue key (e.g. "X000") or numeric issue ID.
        temp_attachment_id: The temporary attachment ID returned by
            ``upload_temporary_attachment``.
        public: ``true`` — visible to customers; ``false`` — internal only.
        comment: (Optional) Comment to accompany the attachment.
    """
    try:
        _check_write(ctx)
        client = _get_client(ctx)
        result = client.add_attachment(
            issue_id_or_key, temp_attachment_id, public=public, comment=comment or None
        )
        return format_json(result)
    except Exception as e:
        return _handle_error(e)
