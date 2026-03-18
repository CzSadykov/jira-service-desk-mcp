"""Tests for formatting utilities."""

from __future__ import annotations

import json

import pytest

from mcp_jira_service_desk.formatting import (
    _safe_get,
    format_approval,
    format_approval_list,
    format_comment,
    format_comment_list,
    format_customer,
    format_customer_list,
    format_customer_request,
    format_customer_request_list,
    format_json,
    format_organization,
    format_organization_list,
    format_participant,
    format_participant_list,
    format_queue,
    format_queue_issue,
    format_queue_issue_list,
    format_queue_list,
    format_request_type,
    format_request_type_fields,
    format_request_type_list,
    format_service_desk,
    format_service_desk_list,
    format_sla,
    format_sla_list,
    format_transition,
    format_transition_list,
)


class TestSafeGet:

    def test_single_key(self):
        assert _safe_get({"a": "val"}, "a") == "val"

    def test_nested_keys(self):
        assert _safe_get({"a": {"b": {"c": "deep"}}}, "a", "b", "c") == "deep"

    def test_missing_key_returns_default(self):
        assert _safe_get({"a": 1}, "x") == "N/A"

    def test_custom_default(self):
        assert _safe_get({}, "x", default="?") == "?"

    def test_none_value_returns_default(self):
        assert _safe_get({"a": None}, "a") == "N/A"

    def test_non_dict_intermediate(self):
        assert _safe_get({"a": "string"}, "a", "b") == "N/A"

    def test_integer_value_converted_to_str(self):
        assert _safe_get({"a": 42}, "a") == "42"


class TestFormatServiceDesk:

    def test_basic(self):
        desk = {"id": "0", "projectKey": "0", "projectName": "Service Desk"}
        result = format_service_desk(desk)
        assert "## Service Desk: Service Desk" in result
        assert "**ID:** 0" in result
        assert "**Key:** 0" in result

    def test_missing_fields(self):
        result = format_service_desk({})
        assert "N/A" in result

    def test_list_empty(self):
        assert format_service_desk_list([]) == "No service desks found."

    def test_list_multiple(self):
        desks = [
            {"id": "0", "projectKey": "0", "projectName": "Desk 1"},
            {"id": "0", "projectKey": "0", "projectName": "Desk 2"},
        ]
        result = format_service_desk_list(desks)
        assert "Desk 1" in result
        assert "Desk 2" in result


class TestFormatRequestType:

    def test_basic(self):
        rt = {
            "id": "0",
            "name": "IT Help",
            "description": "Get IT help",
            "helpText": "Describe issue",
            "serviceDeskId": "0",
        }
        result = format_request_type(rt)
        assert "## Request Type: IT Help" in result
        assert "**ID:** 0" in result
        assert "Get IT help" in result

    def test_with_groups(self):
        rt = {"id": "0", "name": "X", "groupIds": [0, 0]}
        result = format_request_type(rt)
        assert "0" in result

    def test_list_empty(self):
        assert format_request_type_list([]) == "No request types found."


class TestFormatRequestTypeFields:

    def test_with_fields(self):
        data = {
            "requestTypeFields": [
                {
                    "fieldId": "summary",
                    "name": "Summary",
                    "required": True,
                    "description": "Brief description",
                },
                {
                    "fieldId": "priority",
                    "name": "Priority",
                    "required": False,
                    "validValues": [
                        {"label": "High", "value": "0"},
                        {"label": "Low", "value": "0"},
                    ],
                },
            ]
        }
        result = format_request_type_fields(data)
        assert "**Summary**" in result
        assert "Required" in result
        assert "Brief description" in result
        assert "**Priority**" in result
        assert "Optional" in result
        assert "High" in result
        assert "Low" in result

    def test_empty_fields(self):
        assert format_request_type_fields({}) == "No fields found for this request type."
        assert format_request_type_fields({"requestTypeFields": []}) == "No fields found for this request type."


class TestFormatCustomerRequest:

    def test_basic(self):
        req = {
            "issueKey": "0",
            "issueId": "0",
            "reporter": {"displayName": "John", "emailAddress": "john@x.com"},
            "currentStatus": {"status": "Open"},
            "createdDate": {"friendly": "1 hour ago"},
            "requestFieldValues": [
                {"fieldId": "summary", "label": "Summary", "value": "Help me"},
            ],
        }
        result = format_customer_request(req)
        assert "0" in result
        assert "Open" in result
        assert "John" in result
        assert "Help me" in result

    def test_field_value_as_dict(self):
        req = {
            "issueKey": "0",
            "issueId": "0",
            "requestFieldValues": [
                {"fieldId": "priority", "label": "Priority", "value": {"name": "High"}},
            ],
        }
        result = format_customer_request(req)
        assert "High" in result

    def test_list_empty(self):
        assert format_customer_request_list([]) == "No requests found."


class TestFormatQueueIssue:

    def test_issuebean_shape(self, queue_issue_response):
        result = format_queue_issue(queue_issue_response)
        assert "X000" in result
        assert "My keyboard is broken" in result
        assert "Waiting for support" in result
        assert "Fred F. User" in result
        assert "fred@example.com" in result
        assert "2025-10-07T09:30:00.000+0300" in result
        assert "N/A" not in result

    def test_adaptive_visible_fields(self, queue_issue_response):
        result = format_queue_issue(queue_issue_response)
        assert "High" in result
        assert "vip, hardware" in result
        assert "Hardware" in result

    def test_list_empty(self):
        assert format_queue_issue_list([]) == "No requests found."


class TestFormatComment:

    def test_public_comment(self):
        comment = {
            "id": "0",
            "body": "Hello world",
            "public": True,
            "author": {"displayName": "Agent"},
            "created": {"friendly": "5 min ago"},
        }
        result = format_comment(comment)
        assert "Public" in result
        assert "Agent" in result
        assert "Hello world" in result

    def test_internal_comment(self):
        comment = {"id": "0", "body": "Internal note", "public": False, "author": {}}
        result = format_comment(comment)
        assert "Internal" in result

    def test_list_empty(self):
        assert format_comment_list([]) == "No comments found."


class TestFormatCustomer:

    def test_cloud_customer_with_account_id(self):
        c = {"displayName": "Jane", "emailAddress": "jane@x.com", "accountId": "0"}
        result = format_customer(c)
        assert "Jane" in result
        assert "0" in result

    def test_onprem_customer_with_key(self):
        c = {"displayName": "Admin", "emailAddress": "admin@corp.local", "key": "0"}
        result = format_customer(c)
        assert "Admin" in result
        assert "0" in result

    def test_list_empty(self):
        assert format_customer_list([]) == "No customers found."


class TestFormatParticipant:

    def test_cloud_participant(self):
        p = {"displayName": "Bob", "emailAddress": "bob@x.com", "accountId": "0"}
        result = format_participant(p)
        assert "Bob" in result
        assert "0" in result

    def test_onprem_participant_key_fallback(self):
        p = {"displayName": "Bob", "emailAddress": "bob@corp.local", "key": "0"}
        result = format_participant(p)
        assert "0" in result

    def test_list_empty(self):
        assert format_participant_list([]) == "No participants found."


class TestFormatTransition:

    def test_basic(self):
        result = format_transition({"id": "0", "name": "Resolved"})
        assert "Resolved" in result
        assert "0" in result

    def test_list_empty(self):
        assert format_transition_list([]) == "No transitions available."


class TestFormatOrganization:

    def test_basic(self):
        result = format_organization({"id": "0", "name": "Engineering"})
        assert "Engineering" in result
        assert "0" in result

    def test_list_empty(self):
        assert format_organization_list([]) == "No organizations found."


class TestFormatQueue:

    def test_basic(self):
        q = {"id": "0", "name": "Open", "jql": "status = Open"}
        result = format_queue(q)
        assert "Open" in result
        assert "status = Open" in result

    def test_with_issue_count(self):
        q = {"id": "0", "name": "Open", "jql": "status = Open", "issueCount": 42}
        result = format_queue(q)
        assert "42" in result

    def test_without_issue_count(self):
        q = {"id": "0", "name": "Open", "jql": "x"}
        result = format_queue(q)
        assert "Issue Count" not in result

    def test_list_empty(self):
        assert format_queue_list([]) == "No queues found."


class TestFormatSLA:

    def test_with_ongoing_cycle(self):
        sla = {
            "id": "0",
            "name": "Time to resolution",
            "ongoingCycle": {
                "breached": False,
                "paused": False,
                "withinCalendarHours": True,
                "remainingTime": {"friendly": "2h 30m"},
            },
        }
        result = format_sla(sla)
        assert "Time to resolution" in result
        assert "False" in result
        assert "2h 30m" in result

    def test_without_ongoing_cycle(self):
        sla = {"id": "0", "name": "TTR"}
        result = format_sla(sla)
        assert "TTR" in result
        assert "Breached" not in result

    def test_list_empty(self):
        assert format_sla_list([]) == "No SLA information found."


class TestFormatApproval:

    def test_basic(self):
        a = {
            "id": "0",
            "status": "waiting",
            "finalDecision": "pending",
            "canAnswerApproval": True,
            "approvers": [
                {
                    "approver": {"displayName": "Manager"},
                    "approverDecision": "pending",
                }
            ],
        }
        result = format_approval(a)
        assert "waiting" in result
        assert "Manager" in result
        assert "pending" in result

    def test_no_approvers(self):
        a = {"id": "0", "status": "approved", "finalDecision": "approved", "canAnswerApproval": False}
        result = format_approval(a)
        assert "Approvers" not in result

    def test_list_empty(self):
        assert format_approval_list([]) == "No approvals found."


class TestFormatJson:

    def test_basic(self):
        result = format_json({"a": 1, "b": [2, 3]})
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": [2, 3]}

    def test_non_serializable_uses_str(self):
        from datetime import datetime
        result = format_json({"ts": datetime(2025, 1, 1)})
        assert "2025" in result
