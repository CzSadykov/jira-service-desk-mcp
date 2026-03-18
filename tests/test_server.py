"""Tests for MCP server tools — call tool functions directly with fake context."""

from __future__ import annotations

import json

import pytest

from mcp_jira_service_desk.server import (
    add_request_comment,
    add_customers_to_service_desk,
    add_request_participants,
    answer_approval,
    attach_file_to_request,
    create_customer,
    create_customer_request,
    create_organization,
    delete_organization,
    get_approval,
    get_customer_request,
    get_customer_request_status,
    get_request_comment,
    get_request_sla,
    get_request_sla_by_id,
    get_request_type,
    get_request_type_fields,
    get_service_desk,
    get_service_desk_info,
    list_approvals,
    list_customer_transitions,
    list_customers,
    list_issues_in_queue,
    list_my_customer_requests,
    list_organizations,
    list_queues,
    list_request_comments,
    list_request_participants,
    list_request_types,
    list_service_desks,
    mcp,
    perform_transition,
    remove_customers_from_service_desk,
    remove_request_participants,
    upload_temporary_attachment,
)


# ======================================================================
# Read-only mode
# ======================================================================


class TestReadOnlyMode:
    """Write tools must refuse when read_only=True."""

    @pytest.mark.asyncio
    async def test_create_customer_request_blocked(self, fake_readonly_ctx, mock_sd):
        result = await create_customer_request(
            fake_readonly_ctx, "0", "0", '{"summary":"x"}'
        )
        assert "read-only" in result.lower()
        mock_sd.create_customer_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_comment_blocked(self, fake_readonly_ctx, mock_sd):
        result = await add_request_comment(fake_readonly_ctx, "0", "hello")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_create_customer_blocked(self, fake_readonly_ctx, mock_sd):
        result = await create_customer(fake_readonly_ctx, "Joe", "joe@x.com")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_perform_transition_blocked(self, fake_readonly_ctx, mock_sd):
        result = await perform_transition(fake_readonly_ctx, "0", "0")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_create_organization_blocked(self, fake_readonly_ctx, mock_sd):
        result = await create_organization(fake_readonly_ctx, "Org")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_organization_blocked(self, fake_readonly_ctx, mock_sd):
        result = await delete_organization(fake_readonly_ctx, "0")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_add_customers_blocked(self, fake_readonly_ctx, mock_sd):
        result = await add_customers_to_service_desk(fake_readonly_ctx, "0", usernames="alice")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_answer_approval_blocked(self, fake_readonly_ctx, mock_sd):
        result = await answer_approval(fake_readonly_ctx, "0", "0", "approve")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_upload_attachment_blocked(self, fake_readonly_ctx, mock_sd):
        result = await upload_temporary_attachment(fake_readonly_ctx, "0", "/tmp/f.txt")
        assert "read-only" in result.lower()

    @pytest.mark.asyncio
    async def test_attach_file_blocked(self, fake_readonly_ctx, mock_sd):
        result = await attach_file_to_request(fake_readonly_ctx, "0", "0")
        assert "read-only" in result.lower()


class TestToolMetadata:

    @pytest.mark.asyncio
    async def test_all_tools_expose_descriptions(self):
        tools = await mcp.list_tools()
        missing = [tool.name for tool in tools if not (tool.description or "").strip()]
        assert missing == []


# ======================================================================
# Read tools — happy path
# ======================================================================


class TestReadTools:

    @pytest.mark.asyncio
    async def test_get_service_desk_info(self, fake_ctx, mock_sd):
        mock_sd.get_info.return_value = {"version": "5.0.0"}
        result = await get_service_desk_info(fake_ctx)
        assert "5.0.0" in result

    @pytest.mark.asyncio
    async def test_list_service_desks(self, fake_ctx, mock_sd):
        mock_sd.get_service_desks.return_value = {
            "values": [{"id": "0", "projectKey": "0", "projectName": "My Desk"}]
        }
        result = await list_service_desks(fake_ctx)
        assert "My Desk" in result

    @pytest.mark.asyncio
    async def test_get_service_desk(self, fake_ctx, mock_sd):
        mock_sd.get_service_desk_by_id.return_value = {
            "id": "0", "projectKey": "0", "projectName": "Help"
        }
        result = await get_service_desk(fake_ctx, "0")
        assert "Help" in result

    @pytest.mark.asyncio
    async def test_list_request_types(self, fake_ctx, mock_sd):
        mock_sd.get_request_types.return_value = {
            "values": [{"id": "0", "name": "Bug Report"}]
        }
        result = await list_request_types(fake_ctx, "0")
        assert "Bug Report" in result

    @pytest.mark.asyncio
    async def test_get_request_type(self, fake_ctx, mock_sd):
        mock_sd.get_request_type.return_value = {"id": "0", "name": "Bug"}
        result = await get_request_type(fake_ctx, "0", "0")
        assert "Bug" in result

    @pytest.mark.asyncio
    async def test_get_request_type_fields(self, fake_ctx, mock_sd):
        mock_sd.get_request_type_fields.return_value = {
            "requestTypeFields": [{"fieldId": "summary", "name": "Summary", "required": True}]
        }
        result = await get_request_type_fields(fake_ctx, "0", "0")
        assert "Summary" in result

    @pytest.mark.asyncio
    async def test_get_customer_request(self, fake_ctx, mock_sd):
        mock_sd.get_customer_request.return_value = {
            "issueKey": "0", "issueId": "0",
            "reporter": {"displayName": "John"},
            "currentStatus": {"status": "Open"},
        }
        result = await get_customer_request(fake_ctx, "0")
        assert "0" in result

    @pytest.mark.asyncio
    async def test_list_my_customer_requests(self, fake_ctx, mock_sd):
        mock_sd.get_my_customer_requests.return_value = {"values": []}
        result = await list_my_customer_requests(fake_ctx)
        assert "No requests" in result

    @pytest.mark.asyncio
    async def test_get_customer_request_status(self, fake_ctx, mock_sd):
        mock_sd.get_customer_request_status.return_value = {"status": "Waiting for support"}
        result = await get_customer_request_status(fake_ctx, "0")
        assert "Waiting for support" in result

    @pytest.mark.asyncio
    async def test_list_request_comments(self, fake_ctx, mock_sd):
        mock_sd.get_request_comments.return_value = {"values": []}
        result = await list_request_comments(fake_ctx, "0")
        assert "No comments" in result

    @pytest.mark.asyncio
    async def test_get_request_comment(self, fake_ctx, mock_sd):
        mock_sd.get_request_comment_by_id.return_value = {
            "id": "0", "body": "Hello", "public": True, "author": {}
        }
        result = await get_request_comment(fake_ctx, "0", "0")
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_list_customers(self, fake_ctx, mock_sd):
        mock_sd.get_customers.return_value = {"values": []}
        result = await list_customers(fake_ctx, "0")
        assert "No customers" in result

    @pytest.mark.asyncio
    async def test_list_request_participants(self, fake_ctx, mock_sd):
        mock_sd.get_request_participants.return_value = {"values": []}
        result = await list_request_participants(fake_ctx, "0")
        assert "No participants" in result

    @pytest.mark.asyncio
    async def test_list_customer_transitions(self, fake_ctx, mock_sd):
        mock_sd.get_customer_transitions.return_value = {
            "values": [{"id": "0", "name": "Resolve"}]
        }
        result = await list_customer_transitions(fake_ctx, "0")
        assert "Resolve" in result

    @pytest.mark.asyncio
    async def test_list_organizations(self, fake_ctx, mock_sd):
        mock_sd.get_organisations.return_value = {"values": []}
        result = await list_organizations(fake_ctx)
        assert "No organizations" in result

    @pytest.mark.asyncio
    async def test_list_queues(self, fake_ctx, mock_sd):
        mock_sd.get_queues.return_value = {"values": []}
        result = await list_queues(fake_ctx, "0")
        assert "No queues" in result

    @pytest.mark.asyncio
    async def test_list_issues_in_queue(self, fake_ctx, mock_sd):
        mock_sd.get_issues_in_queue.return_value = {"values": []}
        result = await list_issues_in_queue(fake_ctx, "0", "0")
        assert "No requests" in result

    @pytest.mark.asyncio
    async def test_get_request_sla(self, fake_ctx, mock_sd):
        mock_sd.get_sla.return_value = {"values": []}
        result = await get_request_sla(fake_ctx, "0")
        assert "No SLA" in result

    @pytest.mark.asyncio
    async def test_get_request_sla_by_id(self, fake_ctx, mock_sd):
        mock_sd.get_sla_by_id.return_value = {"id": "0", "name": "TTR"}
        result = await get_request_sla_by_id(fake_ctx, "0", "0")
        assert "TTR" in result

    @pytest.mark.asyncio
    async def test_list_approvals(self, fake_ctx, mock_sd):
        mock_sd.get_approvals.return_value = {"values": []}
        result = await list_approvals(fake_ctx, "0")
        assert "No approvals" in result

    @pytest.mark.asyncio
    async def test_get_approval(self, fake_ctx, mock_sd):
        mock_sd.get_approval_by_id.return_value = {"id": "0", "status": "approved"}
        result = await get_approval(fake_ctx, "0", "0")
        assert "approved" in result


# ======================================================================
# Write tools — happy path
# ======================================================================


class TestWriteTools:

    @pytest.mark.asyncio
    async def test_create_customer_request(self, fake_ctx, mock_sd):
        mock_sd.create_customer_request.return_value = {
            "issueKey": "0", "issueId": "0",
            "reporter": {"displayName": "John"},
            "currentStatus": {"status": "Open"},
        }
        result = await create_customer_request(
            fake_ctx, "0", "0", '{"summary": "New request"}'
        )
        assert "0" in result
        mock_sd.create_customer_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_request_invalid_json(self, fake_ctx, mock_sd):
        result = await create_customer_request(fake_ctx, "0", "0", "not-json")
        assert "valid JSON" in result

    @pytest.mark.asyncio
    async def test_create_customer_request_with_participants(self, fake_ctx, mock_sd):
        mock_sd.create_customer_request.return_value = {
            "issueKey": "0", "issueId": "0",
        }
        await create_customer_request(
            fake_ctx, "0", "0", '{"summary":"x"}',
            request_participants="acc1, acc2",
        )
        call_kwargs = mock_sd.create_customer_request.call_args
        assert call_kwargs.kwargs.get("request_participants") == ["acc1", "acc2"]

    @pytest.mark.asyncio
    async def test_add_request_comment(self, fake_ctx, mock_sd):
        mock_sd.create_request_comment.return_value = {
            "id": "0", "body": "Reply", "public": True, "author": {}
        }
        result = await add_request_comment(fake_ctx, "0", "Reply", public=True)
        assert "Reply" in result

    @pytest.mark.asyncio
    async def test_perform_transition(self, fake_ctx, mock_sd):
        mock_sd.perform_transition.return_value = None
        result = await perform_transition(fake_ctx, "0", "0", comment="done")
        assert "successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_create_organization(self, fake_ctx, mock_sd):
        mock_sd.create_organization.return_value = {"id": "0", "name": "New Org"}
        result = await create_organization(fake_ctx, "New Org")
        assert "New Org" in result

    @pytest.mark.asyncio
    async def test_answer_approval(self, fake_ctx, mock_sd):
        mock_sd.answer_approval.return_value = {"id": "0", "status": "approved"}
        result = await answer_approval(fake_ctx, "0", "0", "approve")
        assert "approved" in result


# ======================================================================
# Error handling
# ======================================================================


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_api_error_caught(self, fake_ctx, mock_sd):
        mock_sd.get_info.side_effect = ConnectionError("Connection refused")
        result = await get_service_desk_info(fake_ctx)
        assert "Error:" in result
        assert "Connection refused" in result

    @pytest.mark.asyncio
    async def test_http_error_caught(self, fake_ctx, mock_sd):
        from requests.exceptions import HTTPError
        mock_sd.get_service_desk_by_id.side_effect = HTTPError("404 Not Found")
        result = await get_service_desk(fake_ctx, "999")
        assert "Error:" in result

    @pytest.mark.asyncio
    async def test_generic_exception_caught(self, fake_ctx, mock_sd):
        mock_sd.get_customer_request.side_effect = RuntimeError("Unexpected")
        result = await get_customer_request(fake_ctx, "0")
        assert "Error:" in result
        assert "Unexpected" in result


# ======================================================================
# Comma-separated input parsing
# ======================================================================


class TestInputParsing:

    @pytest.mark.asyncio
    async def test_add_customers_parses_usernames(self, fake_ctx, mock_sd):
        await add_customers_to_service_desk(
            fake_ctx, "0", usernames="alice, bob, charlie"
        )
        mock_sd.add_customers.assert_called_once()
        call_kwargs = mock_sd.add_customers.call_args
        assert call_kwargs.kwargs.get("list_of_usernames") == ["alice", "bob", "charlie"]

    @pytest.mark.asyncio
    async def test_remove_customers_parses_account_ids(self, fake_ctx, mock_sd):
        await remove_customers_from_service_desk(
            fake_ctx, "0", account_ids="0, 0"
        )
        mock_sd.remove_customers.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_participants_parses(self, fake_ctx, mock_sd):
        mock_sd.add_request_participants.return_value = {}
        await add_request_participants(
            fake_ctx, "0", usernames="u1, u2", account_ids="0"
        )
        mock_sd.add_request_participants.assert_called_once_with(
            "0", users_list=["u1", "u2"], account_list=["0"]
        )

    @pytest.mark.asyncio
    async def test_empty_string_gives_none(self, fake_ctx, mock_sd):
        mock_sd.remove_request_participants.return_value = {}
        await remove_request_participants(fake_ctx, "0", usernames="", account_ids="")
        mock_sd.remove_request_participants.assert_called_once_with(
            "0", users_list=[], account_list=[]
        )
