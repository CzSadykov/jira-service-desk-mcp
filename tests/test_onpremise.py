"""On-premise (Server/Data Center) specific integration tests.

On-premise Jira Service Desk differs from Cloud in several ways:
- Authentication via PAT or basic auth (no API tokens)
- Users identified by 'key'/'name' instead of 'accountId'
- Customer management uses usernames, not account IDs
- SSL often disabled or self-signed
- URL schemes may be HTTP (not HTTPS)
- Response shapes can differ slightly (extra fields, different nesting)

These tests verify that the full stack (config → client → server tools)
handles on-premise specifics correctly.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mcp_jira_service_desk.config import ServiceDeskConfig
from mcp_jira_service_desk.client import ServiceDeskClient
from mcp_jira_service_desk.formatting import (
    format_customer,
    format_customer_request,
    format_comment,
    format_organization,
    format_participant,
    format_queue_issue,
    format_queue_list,
    format_sla_list,
    format_transition_list,
    format_approval_list,
)
from mcp_jira_service_desk.server import (
    add_request_comment,
    add_customers_to_service_desk,
    add_request_participants,
    add_users_to_organization,
    create_customer_request,
    get_customer_request,
    get_service_desk,
    list_customer_transitions,
    list_customers,
    list_issues_in_queue,
    list_organizations,
    list_queues,
    list_request_comments,
    get_request_sla,
    list_approvals,
    perform_transition,
    remove_customers_from_service_desk,
    remove_users_from_organization,
)

pytestmark = pytest.mark.onpremise


# ======================================================================
# Config — on-premise specifics
# ======================================================================


class TestOnPremConfig:
    """On-premise configuration edge cases."""

    def test_pat_auth_no_username_needed(self, onprem_pat_config):
        assert onprem_pat_config.auth_type == "pat"
        assert onprem_pat_config.username is None
        assert onprem_pat_config.personal_token is not None

    def test_basic_auth_with_password(self, onprem_basic_config):
        assert onprem_basic_config.auth_type == "basic"
        assert onprem_basic_config.username == "admin"
        assert onprem_basic_config.password == "secret"

    def test_is_cloud_false(self, onprem_pat_config):
        assert onprem_pat_config.is_cloud is False

    def test_ssl_verify_disabled(self, onprem_pat_config):
        assert onprem_pat_config.ssl_verify is False

    def test_http_url_accepted(self, onprem_basic_config):
        assert onprem_basic_config.url.startswith("http://")

    def test_nonstandard_port(self, onprem_basic_config):
        assert "8080" in onprem_basic_config.url


# ======================================================================
# Client — on-premise auth wiring
# ======================================================================


class TestOnPremClientConstruction:

    def test_pat_passes_token_kwarg(self, onprem_pat_config):
        with patch("mcp_jira_service_desk.client.ServiceDesk") as MockSD:
            ServiceDeskClient(onprem_pat_config)
        call_kwargs = MockSD.call_args.kwargs
        assert call_kwargs["token"] == "onprem-pat-token-xyz"
        assert "username" not in call_kwargs
        assert "password" not in call_kwargs
        assert call_kwargs["cloud"] is False
        assert call_kwargs["verify_ssl"] is False

    def test_basic_auth_passes_username_password(self, onprem_basic_config):
        with patch("mcp_jira_service_desk.client.ServiceDesk") as MockSD:
            ServiceDeskClient(onprem_basic_config)
        call_kwargs = MockSD.call_args.kwargs
        assert call_kwargs["username"] == "admin"
        assert call_kwargs["password"] == "secret"
        assert call_kwargs["cloud"] is False


# ======================================================================
# Client — on-premise response handling
# ======================================================================


class TestOnPremResponseFormats:
    """On-prem can return user objects with 'key'/'name' instead of 'accountId'."""

    def test_get_customers_with_key_field(self, onprem_client, mock_sd, onprem_customer_response):
        mock_sd.get_customers.return_value = {"values": [onprem_customer_response]}
        customers = onprem_client.get_customers("0")
        assert len(customers) == 1
        assert customers[0]["key"] == "0"
        assert "accountId" not in customers[0]

    def test_get_customer_request_with_username_reporter(
        self, onprem_client, mock_sd, onprem_request_response
    ):
        mock_sd.get_customer_request.return_value = onprem_request_response
        req = onprem_client.get_customer_request("0")
        assert req["reporter"]["key"] == "0"
        assert req["reporter"]["name"] == "0"

    def test_get_queues_paginated(self, onprem_client, mock_sd, onprem_queue_response):
        mock_sd.get_queues.return_value = onprem_queue_response
        queues = onprem_client.get_queues("0", include_count=True)
        assert len(queues) == 3
        assert queues[2]["name"] == "SLA breached"

    def test_get_sla_with_ongoing_cycle(self, onprem_client, mock_sd, onprem_sla_response):
        mock_sd.get_sla.return_value = onprem_sla_response
        slas = onprem_client.get_sla("0")
        assert len(slas) == 2
        assert slas[0]["ongoingCycle"]["breached"] is False

    def test_get_transitions(self, onprem_client, mock_sd, onprem_transition_response):
        mock_sd.get_customer_transitions.return_value = onprem_transition_response
        transitions = onprem_client.get_customer_transitions("0")
        assert len(transitions) == 3
        names = [t["name"] for t in transitions]
        assert "Resolved" in names
        assert "Closed" in names

    def test_get_approvals(self, onprem_client, mock_sd, onprem_approval_response):
        mock_sd.get_approvals.return_value = onprem_approval_response
        approvals = onprem_client.get_approvals("0")
        assert len(approvals) == 1
        assert approvals[0]["approvers"][0]["approver"]["key"] == "0"


# ======================================================================
# Formatting — on-premise user objects (key instead of accountId)
# ======================================================================


class TestOnPremFormatting:

    def test_format_customer_uses_key_fallback(self, onprem_customer_response):
        result = format_customer(onprem_customer_response)
        assert "Admin User" in result
        assert "admin@corp.local" in result
        assert "0" in result  # key fallback

    def test_format_request_with_key_reporter(self, onprem_request_response):
        result = format_customer_request(onprem_request_response)
        assert "0" in result
        assert "John Smith" in result
        assert "jsmith@corp.local" in result
        assert "VPN not working" in result

    def test_format_comment_with_key_author(self, onprem_comment_response):
        result = format_comment(onprem_comment_response)
        assert "Agent One" in result
        assert "Internal" in result
        assert "Investigating" in result

    def test_format_participant_uses_key_fallback(self):
        p = {
            "key": "0",
            "name": "0",
            "displayName": "John Smith",
            "emailAddress": "jsmith@corp.local",
        }
        result = format_participant(p)
        assert "John Smith" in result
        assert "0" in result

    def test_format_organization_onprem(self, onprem_organization_response):
        result = format_organization(onprem_organization_response)
        assert "Engineering Department" in result

    def test_format_queues_with_counts(self, onprem_queue_response):
        result = format_queue_list(onprem_queue_response["values"])
        assert "All open" in result
        assert "15" in result
        assert "SLA breached" in result
        assert "2" in result

    def test_format_queue_issue_onprem(self, onprem_queue_issue_response):
        result = format_queue_issue(onprem_queue_issue_response)
        assert "X000" in result
        assert "VPN not working" in result
        assert "John Smith" in result
        assert "Remote workforce" in result

    def test_format_sla_list(self, onprem_sla_response):
        result = format_sla_list(onprem_sla_response["values"])
        assert "Time to first response" in result
        assert "2h 45m" in result
        assert "Time to resolution" in result
        assert "22h 45m" in result

    def test_format_transitions(self, onprem_transition_response):
        result = format_transition_list(onprem_transition_response["values"])
        assert "In Progress" in result
        assert "Resolved" in result
        assert "Closed" in result

    def test_format_approvals_with_key_approver(self, onprem_approval_response):
        result = format_approval_list(onprem_approval_response["values"])
        assert "Manager One" in result
        assert "pending" in result


# ======================================================================
# Server tools — on-premise end-to-end (tool → client → mock → format)
# ======================================================================


class TestOnPremServerTools:
    """Full tool invocation with on-premise fixtures."""

    @pytest.mark.asyncio
    async def test_get_customer_request_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_request_response
    ):
        mock_sd.get_customer_request.return_value = onprem_request_response
        result = await get_customer_request(fake_onprem_ctx, "0")
        assert "0" in result
        assert "John Smith" in result
        assert "VPN not working" in result

    @pytest.mark.asyncio
    async def test_list_queues_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_queue_response
    ):
        mock_sd.get_queues.return_value = onprem_queue_response
        result = await list_queues(fake_onprem_ctx, "0", include_count=True)
        assert "All open" in result
        assert "Unassigned" in result
        assert "SLA breached" in result

    @pytest.mark.asyncio
    async def test_list_request_comments_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_comment_response
    ):
        mock_sd.get_request_comments.return_value = {"values": [onprem_comment_response]}
        result = await list_request_comments(fake_onprem_ctx, "0")
        assert "Agent One" in result
        assert "Investigating" in result

    @pytest.mark.asyncio
    async def test_get_sla_onprem(self, fake_onprem_ctx, mock_sd, onprem_sla_response):
        mock_sd.get_sla.return_value = onprem_sla_response
        result = await get_request_sla(fake_onprem_ctx, "0")
        assert "Time to first response" in result
        assert "2h 45m" in result

    @pytest.mark.asyncio
    async def test_list_transitions_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_transition_response
    ):
        mock_sd.get_customer_transitions.return_value = onprem_transition_response
        result = await list_customer_transitions(fake_onprem_ctx, "0")
        assert "In Progress" in result
        assert "Resolved" in result

    @pytest.mark.asyncio
    async def test_list_approvals_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_approval_response
    ):
        mock_sd.get_approvals.return_value = onprem_approval_response
        result = await list_approvals(fake_onprem_ctx, "0")
        assert "Manager One" in result

    @pytest.mark.asyncio
    async def test_list_customers_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_customer_response
    ):
        mock_sd.get_customers.return_value = {"values": [onprem_customer_response]}
        result = await list_customers(fake_onprem_ctx, "0")
        assert "Admin User" in result
        assert "admin@corp.local" in result

    @pytest.mark.asyncio
    async def test_list_organizations_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_organization_response
    ):
        mock_sd.get_organisations.return_value = {"values": [onprem_organization_response]}
        result = await list_organizations(fake_onprem_ctx)
        assert "Engineering Department" in result


# ======================================================================
# On-premise write tools — username-based operations
# ======================================================================


class TestOnPremWriteTools:
    """On-premise uses usernames instead of account IDs for most operations."""

    @pytest.mark.asyncio
    async def test_create_request_with_username_reporter(self, fake_onprem_ctx, mock_sd):
        mock_sd.create_customer_request.return_value = {
            "issueKey": "0", "issueId": "0",
            "reporter": {"key": "0", "displayName": "John Smith"},
            "currentStatus": {"status": "Open"},
        }
        result = await create_customer_request(
            fake_onprem_ctx, "0", "0",
            '{"summary": "VPN access request"}',
            raise_on_behalf_of="0",
        )
        assert "0" in result
        call_kwargs = mock_sd.create_customer_request.call_args.kwargs
        assert call_kwargs["raise_on_behalf_of"] == "0"

    @pytest.mark.asyncio
    async def test_add_comment_internal(self, fake_onprem_ctx, mock_sd, onprem_comment_response):
        mock_sd.create_request_comment.return_value = onprem_comment_response
        result = await add_request_comment(
            fake_onprem_ctx, "0", "Internal investigation note", public=False
        )
        assert "Internal" in result

    @pytest.mark.asyncio
    async def test_add_customers_by_username(self, fake_onprem_ctx, mock_sd):
        await add_customers_to_service_desk(
            fake_onprem_ctx, "0", usernames="0, 0, 0"
        )
        mock_sd.add_customers.assert_called_once_with(
            "0",
            list_of_usernames=["0", "0", "0"],
            list_of_accountids=[],
        )

    @pytest.mark.asyncio
    async def test_remove_customers_by_username(self, fake_onprem_ctx, mock_sd):
        await remove_customers_from_service_desk(
            fake_onprem_ctx, "0", usernames="0"
        )
        mock_sd.remove_customers.assert_called_once_with(
            "0",
            list_of_usernames=["0"],
            list_of_accountids=[],
        )

    @pytest.mark.asyncio
    async def test_add_participants_by_username(self, fake_onprem_ctx, mock_sd):
        mock_sd.add_request_participants.return_value = {}
        await add_request_participants(
            fake_onprem_ctx, "0", usernames="0, 0"
        )
        mock_sd.add_request_participants.assert_called_once_with(
            "0", users_list=["0", "0"], account_list=[]
        )

    @pytest.mark.asyncio
    async def test_add_users_to_org_by_username(self, fake_onprem_ctx, mock_sd):
        await add_users_to_organization(
            fake_onprem_ctx, "0", usernames="0, 0, 0"
        )
        mock_sd.add_users_to_organization.assert_called_once_with(
            "0", users_list=["0", "0", "0"], account_list=[]
        )

    @pytest.mark.asyncio
    async def test_remove_users_from_org_by_username(self, fake_onprem_ctx, mock_sd):
        await remove_users_from_organization(
            fake_onprem_ctx, "0", usernames="0"
        )
        mock_sd.remove_users_from_organization.assert_called_once_with(
            "0", users_list=["0"], account_list=[]
        )

    @pytest.mark.asyncio
    async def test_perform_transition_with_comment(self, fake_onprem_ctx, mock_sd):
        mock_sd.perform_transition.return_value = None
        result = await perform_transition(
            fake_onprem_ctx, "0", "0", comment="Resolved via VPN config fix"
        )
        assert "successfully" in result.lower()
        mock_sd.perform_transition.assert_called_once_with(
            "0", "0", comment="Resolved via VPN config fix"
        )


# ======================================================================
# On-premise — service desk info with on-prem URL
# ======================================================================


class TestOnPremServiceDesk:

    @pytest.mark.asyncio
    async def test_get_service_desk_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_service_desk_response
    ):
        mock_sd.get_service_desk_by_id.return_value = onprem_service_desk_response
        result = await get_service_desk(fake_onprem_ctx, "0")
        assert "IT Service Desk" in result
        assert "0" in result

    @pytest.mark.asyncio
    async def test_list_issues_in_queue_onprem(
        self, fake_onprem_ctx, mock_sd, onprem_queue_issue_response
    ):
        mock_sd.get_issues_in_queue.return_value = {"values": [onprem_queue_issue_response]}
        result = await list_issues_in_queue(fake_onprem_ctx, "0", "0")
        assert "0000" in result
        assert "VPN not working" in result
        assert "Remote workforce" in result


# ======================================================================
# On-premise — error scenarios common in Server/DC
# ======================================================================


class TestOnPremErrors:

    @pytest.mark.asyncio
    async def test_ssl_error_handled(self, fake_onprem_ctx, mock_sd):
        from requests.exceptions import SSLError
        mock_sd.get_info.side_effect = SSLError("SSL certificate verify failed")
        from mcp_jira_service_desk.server import get_service_desk_info
        result = await get_service_desk_info(fake_onprem_ctx)
        assert "Error:" in result
        assert "SSL" in result

    @pytest.mark.asyncio
    async def test_connection_refused_handled(self, fake_onprem_ctx, mock_sd):
        mock_sd.get_service_desks.side_effect = ConnectionError(
            "Connection refused: http://jira.corp.local:8080"
        )
        from mcp_jira_service_desk.server import list_service_desks
        result = await list_service_desks(fake_onprem_ctx)
        assert "Error:" in result
        assert "Connection refused" in result

    @pytest.mark.asyncio
    async def test_401_unauthorized_handled(self, fake_onprem_ctx, mock_sd):
        from requests.exceptions import HTTPError
        mock_sd.get_customer_request.side_effect = HTTPError("401 Unauthorized")
        result = await get_customer_request(fake_onprem_ctx, "0")
        assert "Error:" in result
        assert "401" in result

    @pytest.mark.asyncio
    async def test_403_forbidden_handled(self, fake_onprem_ctx, mock_sd):
        from requests.exceptions import HTTPError
        mock_sd.get_sla.side_effect = HTTPError(
            "403 Forbidden: Only agents can access SLA information"
        )
        result = await get_request_sla(fake_onprem_ctx, "0")
        assert "Error:" in result
        assert "403" in result

    @pytest.mark.asyncio
    async def test_timeout_handled(self, fake_onprem_ctx, mock_sd):
        from requests.exceptions import Timeout
        mock_sd.get_queues.side_effect = Timeout("Request timed out after 75s")
        result = await list_queues(fake_onprem_ctx, "0")
        assert "Error:" in result
        assert "timed out" in result
