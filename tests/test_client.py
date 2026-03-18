"""Tests for ServiceDeskClient — all methods, response normalization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from mcp_jira_service_desk.client import ServiceDeskClient
from mcp_jira_service_desk.config import ServiceDeskConfig


# ======================================================================
# Client construction
# ======================================================================


class TestClientConstruction:

    def test_cloud_token_auth_kwargs(self, cloud_config):
        with patch("mcp_jira_service_desk.client.ServiceDesk") as MockSD:
            ServiceDeskClient(cloud_config)
        MockSD.assert_called_once_with(
            url="https://test.atlassian.net",
            cloud=True,
            verify_ssl=True,
            username="user@test.com",
            password="cloud-api-token",
        )

    def test_onprem_pat_auth_kwargs(self, onprem_pat_config):
        with patch("mcp_jira_service_desk.client.ServiceDesk") as MockSD:
            ServiceDeskClient(onprem_pat_config)
        MockSD.assert_called_once_with(
            url="https://jira.corp.local",
            cloud=False,
            verify_ssl=False,
            token="onprem-pat-token-xyz",
        )

    def test_onprem_basic_auth_kwargs(self, onprem_basic_config):
        with patch("mcp_jira_service_desk.client.ServiceDesk") as MockSD:
            ServiceDeskClient(onprem_basic_config)
        MockSD.assert_called_once_with(
            url="http://jira.corp.local:8080",
            cloud=False,
            verify_ssl=False,
            username="admin",
            password="secret",
        )


# ======================================================================
# Response normalization — "values" dict, list, single, None
# ======================================================================


class TestResponseNormalization:
    """Methods that return lists should normalize paginated Jira responses."""

    @pytest.mark.parametrize("method_name,call_args", [
        ("get_service_desks", ()),
        ("get_request_types", ("0",)),
        ("get_my_customer_requests", ()),
        ("get_request_comments", ("0",)),
        ("get_customers", ("0",)),
        ("get_request_participants", ("0",)),
        ("get_customer_transitions", ("0",)),
        ("get_organizations", ()),
        ("get_users_in_organization", ("0",)),
        ("get_queues", ("0",)),
        ("get_issues_in_queue", ("0", "0")),
        ("get_sla", ("0",)),
        ("get_approvals", ("0",)),
    ])
    def test_dict_with_values_key(self, cloud_client, mock_sd, method_name, call_args):
        items = [{"id": "0"}, {"id": "0"}]
        sd_method_map = {
            "get_service_desks": "get_service_desks",
            "get_request_types": "get_request_types",
            "get_my_customer_requests": "get_my_customer_requests",
            "get_request_comments": "get_request_comments",
            "get_customers": "get_customers",
            "get_request_participants": "get_request_participants",
            "get_customer_transitions": "get_customer_transitions",
            "get_organizations": "get_organisations",
            "get_users_in_organization": "get_users_in_organization",
            "get_queues": "get_queues",
            "get_issues_in_queue": "get_issues_in_queue",
            "get_sla": "get_sla",
            "get_approvals": "get_approvals",
        }
        sd_method = sd_method_map[method_name]
        getattr(mock_sd, sd_method).return_value = {"values": items, "size": 2}

        result = getattr(cloud_client, method_name)(*call_args)
        assert result == items

    @pytest.mark.parametrize("method_name,call_args", [
        ("get_service_desks", ()),
        ("get_request_types", ("0",)),
    ])
    def test_plain_list_passthrough(self, cloud_client, mock_sd, method_name, call_args):
        items = [{"id": "0"}]
        sd_method_map = {
            "get_service_desks": "get_service_desks",
            "get_request_types": "get_request_types",
        }
        getattr(mock_sd, sd_method_map[method_name]).return_value = items
        result = getattr(cloud_client, method_name)(*call_args)
        assert result == items

    @pytest.mark.parametrize("method_name,call_args", [
        ("get_service_desks", ()),
        ("get_request_types", ("0",)),
    ])
    def test_single_item_wrapped(self, cloud_client, mock_sd, method_name, call_args):
        item = {"id": "0"}
        sd_method_map = {
            "get_service_desks": "get_service_desks",
            "get_request_types": "get_request_types",
        }
        getattr(mock_sd, sd_method_map[method_name]).return_value = item
        result = getattr(cloud_client, method_name)(*call_args)
        assert result == [item]

    def test_none_returns_empty_list(self, cloud_client, mock_sd):
        mock_sd.get_service_desks.return_value = None
        assert cloud_client.get_service_desks() == []


# ======================================================================
# Passthrough methods (no normalization)
# ======================================================================


class TestPassthroughMethods:

    def test_get_info(self, cloud_client, mock_sd):
        mock_sd.get_info.return_value = {"version": "5.0.0"}
        assert cloud_client.get_info() == {"version": "5.0.0"}

    def test_get_service_desk_by_id(self, cloud_client, mock_sd):
        desk = {"id": "0", "projectName": "SD"}
        mock_sd.get_service_desk_by_id.return_value = desk
        assert cloud_client.get_service_desk_by_id("0") == desk
        mock_sd.get_service_desk_by_id.assert_called_once_with("0")

    def test_get_request_type(self, cloud_client, mock_sd):
        rt = {"id": "0", "name": "Bug"}
        mock_sd.get_request_type.return_value = rt
        assert cloud_client.get_request_type("0", "0") == rt
        mock_sd.get_request_type.assert_called_once_with("0", "0")

    def test_get_request_type_fields(self, cloud_client, mock_sd):
        data = {"requestTypeFields": []}
        mock_sd.get_request_type_fields.return_value = data
        assert cloud_client.get_request_type_fields("0", "0") == data

    def test_get_customer_request(self, cloud_client, mock_sd):
        req = {"issueKey": "0"}
        mock_sd.get_customer_request.return_value = req
        assert cloud_client.get_customer_request("0") == req

    def test_get_customer_request_status(self, cloud_client, mock_sd):
        status = {"status": "Open"}
        mock_sd.get_customer_request_status.return_value = status
        assert cloud_client.get_customer_request_status("0") == status

    def test_get_request_comment_by_id(self, cloud_client, mock_sd):
        comment = {"id": "0", "body": "hello"}
        mock_sd.get_request_comment_by_id.return_value = comment
        assert cloud_client.get_request_comment_by_id("0", "0") == comment

    def test_get_organization(self, cloud_client, mock_sd):
        org = {"id": "0", "name": "Eng"}
        mock_sd.get_organization.return_value = org
        assert cloud_client.get_organization("0") == org

    def test_get_sla_by_id(self, cloud_client, mock_sd):
        sla = {"id": "0", "name": "TTR"}
        mock_sd.get_sla_by_id.return_value = sla
        assert cloud_client.get_sla_by_id("0", "0") == sla

    def test_get_approval_by_id(self, cloud_client, mock_sd):
        appr = {"id": "0", "status": "waiting"}
        mock_sd.get_approval_by_id.return_value = appr
        assert cloud_client.get_approval_by_id("0", "0") == appr


# ======================================================================
# Write operations — verify correct args passed to _sd
# ======================================================================


class TestWriteOperations:

    def test_create_customer_request(self, cloud_client, mock_sd):
        mock_sd.create_customer_request.return_value = {"issueKey": "0"}
        result = cloud_client.create_customer_request(
            "0", "0", {"summary": "test"}, raise_on_behalf_of="user1"
        )
        mock_sd.create_customer_request.assert_called_once_with(
            service_desk_id="0",
            request_type_id="0",
            values_dict={"summary": "test"},
            raise_on_behalf_of="user1",
            request_participants=None,
        )
        assert result["issueKey"] == "0"

    def test_create_request_comment(self, cloud_client, mock_sd):
        mock_sd.create_request_comment.return_value = {"id": "0"}
        cloud_client.create_request_comment("0", "hello", public=False)
        mock_sd.create_request_comment.assert_called_once_with("0", "hello", public=False)

    def test_create_customer(self, cloud_client, mock_sd):
        mock_sd.create_customer.return_value = {"displayName": "Joe"}
        cloud_client.create_customer("Joe Doe", "joe@test.com")
        mock_sd.create_customer.assert_called_once_with("Joe Doe", "joe@test.com")

    def test_add_customers_usernames(self, cloud_client, mock_sd):
        cloud_client.add_customers("0", usernames=["alice", "bob"])
        mock_sd.add_customers.assert_called_once_with(
            "0", list_of_usernames=["alice", "bob"], list_of_accountids=[]
        )

    def test_add_customers_account_ids(self, cloud_client, mock_sd):
        cloud_client.add_customers("0", account_ids=["0", "0"])
        mock_sd.add_customers.assert_called_once_with(
            "0", list_of_usernames=[], list_of_accountids=["0", "0"]
        )

    def test_remove_customers(self, cloud_client, mock_sd):
        cloud_client.remove_customers("0", usernames=["alice"])
        mock_sd.remove_customers.assert_called_once_with(
            "0", list_of_usernames=["alice"], list_of_accountids=[]
        )

    def test_add_request_participants(self, cloud_client, mock_sd):
        mock_sd.add_request_participants.return_value = {}
        cloud_client.add_request_participants("0", usernames=["u1"], account_ids=["0"])
        mock_sd.add_request_participants.assert_called_once_with(
            "0", users_list=["u1"], account_list=["0"]
        )

    def test_remove_request_participants(self, cloud_client, mock_sd):
        mock_sd.remove_request_participants.return_value = {}
        cloud_client.remove_request_participants("0", account_ids=["0"])
        mock_sd.remove_request_participants.assert_called_once_with(
            "0", users_list=[], account_list=["0"]
        )

    def test_perform_transition(self, cloud_client, mock_sd):
        cloud_client.perform_transition("0", "0", comment="done")
        mock_sd.perform_transition.assert_called_once_with("0", "0", comment="done")

    def test_create_organization(self, cloud_client, mock_sd):
        mock_sd.create_organization.return_value = {"id": "0", "name": "New"}
        cloud_client.create_organization("New")
        mock_sd.create_organization.assert_called_once_with("New")

    def test_delete_organization(self, cloud_client, mock_sd):
        cloud_client.delete_organization("0")
        mock_sd.delete_organization.assert_called_once_with("0")

    def test_add_organization(self, cloud_client, mock_sd):
        cloud_client.add_organization("0", 0)
        mock_sd.add_organization.assert_called_once_with("0", 0)

    def test_remove_organization(self, cloud_client, mock_sd):
        cloud_client.remove_organization("0", 0)
        mock_sd.remove_organization.assert_called_once_with("0", 0)

    def test_add_users_to_organization(self, cloud_client, mock_sd):
        cloud_client.add_users_to_organization("0", usernames=["u1"])
        mock_sd.add_users_to_organization.assert_called_once_with(
            "0", users_list=["u1"], account_list=[]
        )

    def test_remove_users_from_organization(self, cloud_client, mock_sd):
        cloud_client.remove_users_from_organization("0", account_ids=["0"])
        mock_sd.remove_users_from_organization.assert_called_once_with(
            "0", users_list=[], account_list=["0"]
        )

    def test_answer_approval(self, cloud_client, mock_sd):
        mock_sd.answer_approval.return_value = {"id": "0", "status": "approved"}
        cloud_client.answer_approval("0", "0", "approve")
        mock_sd.answer_approval.assert_called_once_with("0", "0", "approve")

    def test_attach_temporary_file(self, cloud_client, mock_sd):
        mock_sd.attach_temporary_file.return_value = {"temporaryAttachmentId": "0"}
        cloud_client.attach_temporary_file("0", "/tmp/file.txt")
        mock_sd.attach_temporary_file.assert_called_once_with("0", "/tmp/file.txt")

    def test_add_attachment(self, cloud_client, mock_sd):
        mock_sd.add_attachment.return_value = {}
        cloud_client.add_attachment("0", "0", public=False, comment="see attached")
        mock_sd.add_attachment.assert_called_once_with(
            "0", "0", public=False, comment="see attached"
        )
